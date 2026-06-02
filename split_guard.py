import sys

def main():
    file_path = "backend/app/api/v1/_guard_old.py"
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # The file has imports at the top (lines 0 to 166 or so)
    imports_end = 0
    for i, line in enumerate(lines):
        if "@router.post(\"/scan\"" in line:
            imports_end = i
            break
    
    imports = lines[:imports_end]
    
    # We will write the imports and specific sections to each file
    def write_module(filename, sections):
        with open(filename, "w", encoding="utf-8") as f:
            f.writelines(imports)
            for start, end in sections:
                f.writelines(lines[start:end])

    # Find the boundaries of the first instance of each endpoint
    def find_endpoint(decorator):
        for i, line in enumerate(lines):
            if decorator in line:
                # Find the next decorator to determine the end
                for j in range(i+1, len(lines)):
                    if line.startswith("@router"):
                        return i, j
                return i, len(lines)
        return -1, -1

    # Approximate line numbers based on previous search
    # /scan 166 to 273 (where /explain starts)
    # /explain 273 to 388 (where /health starts)
    # /health 388 to 398
    # /info 398 to 424
    # /history 424 to 457
    # /stats 457 to 602
    # /config 602 to 668
    # /scan/batch 668 to 781

    # Let's dynamically find them by looking for the next router
    def get_bounds(start_line_prefix):
        start = -1
        for i, line in enumerate(lines):
            if line.startswith(start_line_prefix):
                start = i
                break
        if start == -1: return -1, -1
        
        end = len(lines)
        for i in range(start + 1, len(lines)):
            if lines[i].startswith("@router"):
                end = i
                break
        return start, end

    scan_start, scan_end = get_bounds('@router.post("/scan", response_model=ScanResponse)')
    batch_start, batch_end = get_bounds('@router.post("/scan/batch"')
    explain_start, explain_end = get_bounds('@router.post(') # /explain spans multiple lines
    health_start, health_end = get_bounds('@router.get("/health"')
    info_start, info_end = get_bounds('@router.get("/info"')
    history_start, history_end = get_bounds('@router.get("/history"')
    stats_start, stats_end = get_bounds('@router.get("/stats"')
    config_get_start, config_get_end = get_bounds('@router.get("/config"')
    config_patch_start, config_patch_end = get_bounds('@router.patch("/config"')

    # Write scan.py
    write_module("backend/app/api/v1/guard/scan.py", [(scan_start, scan_end), (batch_start, batch_end)])
    
    # Write explain.py
    write_module("backend/app/api/v1/guard/explain.py", [(explain_start, health_start)])
    
    # Write health.py
    write_module("backend/app/api/v1/guard/health.py", [(health_start, health_end), (info_start, info_end)])
    
    # Write stats.py
    write_module("backend/app/api/v1/guard/stats.py", [(history_start, history_end), (stats_start, stats_end)])
    
    # Write config.py
    write_module("backend/app/api/v1/guard/config.py", [(config_get_start, config_get_end), (config_patch_start, config_patch_end)])

    # Write __init__.py
    with open("backend/app/api/v1/guard/__init__.py", "w", encoding="utf-8") as f:
        f.write("from fastapi import APIRouter\n")
        f.write("from .scan import router as scan_router\n")
        f.write("from .explain import router as explain_router\n")
        f.write("from .stats import router as stats_router\n")
        f.write("from .config import router as config_router\n")
        f.write("from .health import router as health_router\n\n")
        f.write("router = APIRouter()\n")
        f.write("router.include_router(scan_router)\n")
        f.write("router.include_router(explain_router)\n")
        f.write("router.include_router(stats_router)\n")
        f.write("router.include_router(config_router)\n")
        f.write("router.include_router(health_router)\n")

if __name__ == "__main__":
    main()
