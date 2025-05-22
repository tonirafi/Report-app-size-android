#!/usr/bin/env python3
import zipfile, argparse, textwrap, sys, csv, os

# Utility to format bytes to human-readable MB
def human(bytes_size):
    return f"{bytes_size/1024/1024:.1f} MB"

# Analyze sizes per module based on patterns, return list of dicts and total comp/uncomp bytes
def analyze(apk_path, modules, prefix=""):
    z = zipfile.ZipFile(apk_path, 'r')
    infos = z.infolist()

    total_comp   = sum(i.compress_size for i in infos)
    total_uncomp = sum(i.file_size     for i in infos)

    rows = []
    for name, patterns in modules.items():
        comp = 0
        uncomp = 0
        for i in infos:
            if any(i.filename.startswith(prefix + p) for p in patterns):
                comp   += i.compress_size
                uncomp += i.file_size
        rows.append({
            'SDK / Feature': name,
            'Original Install (MB)': human(comp),
            'Original After Decompress (MB)': human(uncomp),
            'Remaining Install (MB)': human(total_comp - comp),
            'Remaining After Decompress (MB)': human(total_uncomp - uncomp),
            'Delta Install (MB)': human(comp),
            'Delta After Decompress (MB)': human(uncomp)
        })
    return rows, total_comp, total_uncomp

# Generate modules dict automatically from assets/ and lib/ structure
def generate_modules(apk_path, prefix=""):
    z = zipfile.ZipFile(apk_path, 'r')
    paths = sorted({i.filename for i in z.infolist()})
    asset_mods = {}
    lib_mods = {}
    # assets: group by top-level path element
    for p in paths:
        if p.startswith(prefix + 'assets/'):
            parts = p.split('/')
            key = parts[1]
            asset_mods.setdefault(key, []).append(f"assets/{key}/")
    # lib: group by library base name
    for p in paths:
        if p.startswith(prefix + 'lib/') and p.endswith('.so'):
            parts = p.split('/')
            if len(parts) >= 3:
                abi = parts[1]
                libname = parts[2]
                key = libname.replace('.so', '')
                lib_mods.setdefault(key, []).append(f"lib/{abi}/{libname}")
    # merge into full modules
    modules = {**{k: sorted(set(v)) for k, v in asset_mods.items()},
               **{k: sorted(set(v)) for k, v in lib_mods.items()}}
    return modules, set(asset_mods.keys()), set(lib_mods.keys())

# Parse "X MB" to float MB
def parse_mb(s):
    try:
        return float(s.split()[0])
    except:
        return 0.0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description=textwrap.dedent("""
            Hitung size per SDK/feature dalam APK.

            --show-structure : list paths;
            --gen            : generate modules mapping;
            --type TYPE      : filter by 'asset', 'lib', atau 'all';
            --excel, --csv, --md : output format.
        """))
    parser.add_argument("apk", help="Path ke file .apk atau .aab")
    parser.add_argument("--show-structure", action="store_true",
                        help="Tampilkan daftar path di lib/ dan assets/")
    parser.add_argument("--gen", action="store_true",
                        help="Generate modules mapping otomatis")
    parser.add_argument("--type", choices=["asset", "lib", "all"], default="all",
                        help="Filter modul")
    parser.add_argument("--excel", metavar="FILE.xlsx",
                        help="Export ke Excel (.xlsx)")
    parser.add_argument("--csv", metavar="FILE.csv",
                        help="Export ke CSV (.csv)")
    parser.add_argument("--md", metavar="FILE.md",
                        help="Export ke Markdown (.md)")
    args = parser.parse_args()

    if args.show_structure:
        z = zipfile.ZipFile(args.apk, 'r')
        paths = sorted({i.filename for i in z.infolist()})
        print("== FILES DI lib/ ==")
        for p in paths:
            if p.startswith("lib/"):
                print("  " + p)
        print("\n== FILES DI assets/ ==")
        for p in paths:
            if p.startswith("assets/"):
                print("  " + p)
        sys.exit(0)

    modules, asset_keys, lib_keys = generate_modules(args.apk)
    if args.gen:
        print("# modules mapping:")
        print("modules = {")
        for k, lst in modules.items():
            print(f"  '{k}': {lst},")
        print("}")

    if args.type == "asset":
        modules = {k: v for k, v in modules.items() if k in asset_keys}
    elif args.type == "lib":
        modules = {k: v for k, v in modules.items() if k in lib_keys}

    # Analyze modules and get APK totals
    results, total_comp_bytes, total_uncomp_bytes = analyze(args.apk, modules)
    # Compute App (base project) row
    module_comp_bytes = sum(parse_mb(r['Original Install (MB)']) * 1024 * 1024 for r in results)
    module_uncomp_bytes = sum(parse_mb(r['Original After Decompress (MB)']) * 1024 * 1024 for r in results)
    app_comp = total_comp_bytes - module_comp_bytes
    app_uncomp = total_uncomp_bytes - module_uncomp_bytes
    # Append App row
    results.append({
        'SDK / Feature': 'App',
        'Original Install (MB)': human(app_comp),
        'Original After Decompress (MB)': human(app_uncomp),
        'Remaining Install (MB)': human(total_comp_bytes - app_comp),
        'Remaining After Decompress (MB)': human(total_uncomp_bytes - app_uncomp),
        'Delta Install (MB)': human(app_comp),
        'Delta After Decompress (MB)': human(app_uncomp)
    })

    # Annotate Type and sort
    for r in results:
        name = r['SDK / Feature']
        if name in asset_keys:
            r['Type'] = 'Asset'
        elif name in lib_keys:
            r['Type'] = 'Library'
        else:
            r['Type'] = 'App'
    results.sort(key=lambda r: parse_mb(r['Original Install (MB)']), reverse=True)

    # Calculate totals per Type and overall
    totals = {}
    for r in results:
        t = r['Type']
        vals = totals.setdefault(t, {'Original Install (MB)': 0.0, 'Original After Decompress (MB)': 0.0})
        vals['Original Install (MB)'] += parse_mb(r['Original Install (MB)'])
        vals['Original After Decompress (MB)'] += parse_mb(r['Original After Decompress (MB)'])
    overall = {
        'Original Install (MB)': sum(v['Original Install (MB)'] for v in totals.values()),
        'Original After Decompress (MB)': sum(v['Original After Decompress (MB)'] for v in totals.values())
    }

    # Build summary
    summary_lines = ["### 📊 Summary per Type", ""]
    for t, v in totals.items():
        summary_lines.append(f"- **{t}**: {v['Original Install (MB)']:.1f} MB (compressed), {v['Original After Decompress (MB)']:.1f} MB (decompressed)")
    summary_lines.append("")
    summary_lines.append(f"**Total APK Overall**: {overall['Original Install (MB)']:.1f} MB (compressed), {overall['Original After Decompress (MB)']:.1f} MB (decompressed)")
    summary_lines.append("")

    # Prepare Markdown table
    md_cols = ['Type','SDK / Feature','Original Install (MB)','Original After Decompress (MB)',
               'Remaining Install (MB)','Remaining After Decompress (MB)',
               'Delta Install (MB)','Delta After Decompress (MB)']
    title = "## 📦 APK Size Breakdown per Module"
    subtitle = textwrap.dedent("""
    Kolom | Penjelasan
    :--|:--
    **Type** | Jenis modul: 'Asset', 'Library', atau 'App'.
    **SDK / Feature** | Nama modul atau App.
    **Original Install (MB)** | Ukuran terkompresi.
    **Original After Decompress (MB)** | Ukuran dekompresi.
    **Remaining Install (MB)** | Sisa compressed.
    **Remaining After Decompress (MB)** | Sisa decompressed.
    **Delta Install (MB)** | Perubahan compressed.
    **Delta After Decompress (MB)** | Perubahan decompressed.
    """)
    widths=[max(len(c),max((len(r[c]) for r in results),default=0)) for c in md_cols]
    widths[0]=max(widths[0],len('Total'))
    md_header="| "+" | ".join(c.ljust(widths[i]) for i,c in enumerate(md_cols))+" |"
    md_sep="| "+" | ".join('-'*widths[i] for i in range(len(md_cols)))+" |"

    report_lines=summary_lines+[title,"",subtitle,md_header,md_sep]
    for r in results:
        report_lines.append("| "+" | ".join(r[c].ljust(widths[i]) for i,c in enumerate(md_cols))+" |")
    report_lines.append(md_sep)
    for t,v in totals.items():
        report_lines.append("| "+" | ".join([
            'Total'.ljust(widths[0]),t.ljust(widths[1]),
            f"{v['Original Install (MB)']:.1f} MB".ljust(widths[2]),
            f"{v['Original After Decompress (MB)']:.1f} MB".ljust(widths[3]),
            *(['']*4)
        ])+" |")
    report_lines.append(md_sep)
    report_lines.append("| "+" | ".join([
        'Total'.ljust(widths[0]),'Keseluruhan'.ljust(widths[1]),
        f"{overall['Original Install (MB)']:.1f} MB".ljust(widths[2]),
        f"{overall['Original After Decompress (MB)']:.1f} MB".ljust(widths[3]),
        *(['']*4)
    ])+" |")

    # Output
    if args.excel:
        import pandas as pd

        # Hapus file Excel lama jika ada
        if os.path.exists(args.excel):
            os.remove(args.excel)

        df = pd.DataFrame(results)
        for t, v in totals.items():
            df = pd.concat([df, pd.DataFrame([{
                'Type': 'Total', 'SDK / Feature': t,
                'Original Install (MB)': f"{v['Original Install (MB)']:.1f} MB",
                'Original After Decompress (MB)': f"{v['Original After Decompress (MB)']:.1f} MB"
            }])], ignore_index=True)
        df = pd.concat([df, pd.DataFrame([{
            'Type': 'Total', 'SDK / Feature': 'Keseluruhan',
            'Original Install (MB)': f"{overall['Original Install (MB)']:.1f} MB",
            'Original After Decompress (MB)': f"{overall['Original After Decompress (MB)']:.1f} MB"
        }])], ignore_index=True)

        # === Tambahan: detail file App ===
        z = zipfile.ZipFile(args.apk, 'r')
        all_files = set(i.filename for i in z.infolist())
        used_files = set()
        for patterns in modules.values():
            for p in patterns:
                used_files.update(f for f in all_files if f.startswith(p))
        app_files = sorted(all_files - used_files)
        app_file_rows = []
        for f in app_files:
            info = z.getinfo(f)
            app_file_rows.append({
                'File': f,
                'Compressed Size (B)': int(info.compress_size),
                'Uncompressed Size (B)': int(info.file_size),
                'Compressed Size (MB)': f"{info.compress_size/1024/1024:.3f}",
                'Uncompressed Size (MB)': f"{info.file_size/1024/1024:.3f}"
            })
        app_df = pd.DataFrame(app_file_rows)
        # Urutkan berdasarkan Uncompressed Size (B) terbesar ke terkecil
        if not app_df.empty:
            app_df = app_df.sort_values(by='Uncompressed Size (B)', ascending=False)

        # Pastikan tidak ada kolom bertipe object (list/dict)
        for col in df.columns:
            if df[col].apply(lambda x: isinstance(x, (list, dict))).any():
                df[col] = df[col].astype(str)
        for col in app_df.columns:
            if app_df[col].apply(lambda x: isinstance(x, (list, dict))).any():
                app_df[col] = app_df[col].astype(str)

        try:
            with pd.ExcelWriter(args.excel, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Summary')
                if not app_df.empty:
                    app_df.to_excel(writer, index=False, sheet_name='App_Detail')
                else:
                    # Sheet kosong, tulis satu baris dummy agar Excel tidak error
                    pd.DataFrame([{'File': 'No data'}]).to_excel(writer, index=False, sheet_name='App_Detail')
            print(f"✅ Excel saved to {args.excel}")
            print("Excel writing done, file size:", os.path.getsize(args.excel))
        except Exception as e:
            print("❌ Error saat menulis Excel:", e)
    elif args.csv:
        with open(args.csv,'w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=md_cols)
            w.writeheader();w.writerows(results)
            for t,v in totals.items():
                row={'':None}
                row={col:'' for col in md_cols}
                row['Type']='Total';row['SDK / Feature']=t
                row['Original Install (MB)']=f"{v['Original Install (MB)']:.1f} MB"
                row['Original After Decompress (MB)']=f"{v['Original After Decompress (MB)']:.1f} MB"
                w.writerow(row)
            row={col:'' for col in md_cols}
            row['Type']='Total';row['SDK / Feature']='Keseluruhan'
            row['Original Install (MB)']=f"{overall['Original Install (MB)']:.1f} MB"
            row['Original After Decompress (MB)']=f"{overall['Original After Decompress (MB)']:.1f} MB"
            w.writerow(row)
        print(f"✅ CSV saved ke {args.csv}")
    elif args.md:
        with open(args.md,'w') as f: f.write("\n".join(report_lines))
        print(f"✅ Markdown saved ke {args.md}")
    else:
        print("\n".join(report_lines))
