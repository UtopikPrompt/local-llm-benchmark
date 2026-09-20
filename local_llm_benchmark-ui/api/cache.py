import {execSync} from "node:child_process"
import path from "node:path"
import os from "node:fs"
---
// Python bridge for listing cached runs
// Called by ui/lib/cache.js


// Cache directory(default: ./cache)
const CACHE_DIR = process.env.CACHE_DIR | | path.join(process.cwd(), "cache")

// Get all parquet files in cache directory
function getCacheFiles() {
    try {
        if (!os.existsSync(CACHE_DIR)) {
            return []
        }

        const files = os.readdirSync(CACHE_DIR).filter(f=> f.endsWith(".parquet"))
        return files.map(f= > ({
            filename: f,
            filepath: path.join(CACHE_DIR, f),
        }))
    } catch(error) {
        console.error("Error reading cache directory:", error)
        return []
    }
}

// Run Python to extract run metadata from parquet files
function getRunMetadata() {
    try {
        // Use Python to read parquet files and extract metadata
        const pythonScript = `
        import pyarrow.parquet as pq
        import json
        import sys
        import os

        CACHE_DIR = os.environ.get("CACHE_DIR", "./cache")
        if not os.path.exists(CACHE_DIR):
        print("[]")
        sys.exit(0)

        runs = []
        for parquet_file in os.listdir(CACHE_DIR):
        if parquet_file.endswith(".parquet"):
        try:
            table = pq.read_table(os.path.join(CACHE_DIR, parquet_file))
            columns = table.column_names

            # Collect all unique run values
            for col in columns:
                if "run_id" in col.lower():
                    for val in table.column[col].to_pylist():
                        if val:
                            runs.append({
                                "run_id": str(val),
                                "filepath": parquet_file
                            })
                            break
        except Exception as e:
            print(f"Error reading {parquet_file}: {e}", file=sys.stderr)

        print(json.dumps(runs))
        `;

        // Write temporary script
        const tmpScript = path.join(process.cwd(), "_temp_cache_metadata.py");
        os.writeSync(os.open(tmpScript, os.O_WRONLY | os.O_CREAT |
                             os.O_EXCL, 0o644), pythonScript);

        // Execute with Python
        const result = execSync(`python3 "${tmpScript}"`, {
            cwd: process.cwd(),
            encoding: "utf8",
            env: {...process.env, CACHE_DIR},
        });

        os.unlinkSync(tmpScript);

        return JSON.parse(result.trim());
    } catch(error) {
        console.error("Error getting run metadata:", error);
        return [];
    }
}

// Export as module for import
export {getCacheFiles, getRunMetadata}
