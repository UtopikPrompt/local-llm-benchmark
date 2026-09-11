// Tests for result-row serialization: :func:`rowToObject`, :data:`CSV_COLUMNS`,
// :func:`writeJSON`, :func:`writeCSV`, :func:`writeReport`, :func:`printSummary`.
//
// Mirrors tests/test_report.py. The TS migration dropped the Row class in
// favour of a plain interface + rowToObject(), so these tests assert the
// serialized shape, JSON/CSV dispatch, and the printed summary.

import { describe, expect, it } from "vitest";
import { writeFileSync, readFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  rowToObject,
  writeCSV,
  writeJSON,
  writeReport,
  printSummary,
} from "../lib/report.js";
import { CSV_COLUMNS, type Row } from "../lib/results.js";

const read = (path: string) => readFileSync(path, "utf-8");

const _rows = (): Row[] => [
  {
    engine: "engine-a",
    model: "m1",
    judge: "judge",
    task_id: "qa-1",
    category: "qa",
    prompt: "p1",
    expected: "2007",
    output: "answer",
    ttft_s: 0.5,
    tok_per_s: 100.0,
    iters_per_s: 3.0,
    quality_passed: true,
    quality_deterministic: true,
    quality_judge: true,
    quality_note: "ok",
  },
  {
    engine: "engine-a",
    model: "m2",
    judge: "",
    task_id: "qa-2",
    category: "math",
    prompt: "p2",
    expected: "",
    output: "",
    ttft_s: 0.0,
    tok_per_s: 0.0,
    iters_per_s: 0.0,
    quality_passed: false,
    quality_deterministic: false,
    quality_judge: false,
    quality_note: "fail",
  },
];

// --- rowToObject -----------------------------------------------------------

describe("rowToObject", () => {
  it("produces the documented field order", () => {
    const row = _rows()[0];
    expect(Object.keys(rowToObject(row)).sort()).toEqual(
      [
        "category",
        "engine",
        "expected",
        "iters_per_s",
        "judge",
        "model",
        "output",
        "prompt",
        "quality_deterministic",
        "quality_judge",
        "quality_note",
        "quality_passed",
        "task_id",
        "ttft_s",
        "tok_per_s",
      ].sort(),
    );
  });

  it("maps each field", () => {
    const row = rowToObject(_rows()[0]);
    expect(row).toMatchObject({
      engine: "engine-a",
      model: "m1",
      judge: "judge",
      task_id: "qa-1",
      category: "qa",
      prompt: "p1",
      expected: "2007",
      output: "answer",
      ttft_s: 0.5,
      tok_per_s: 100.0,
      iters_per_s: 3.0,
      quality_passed: true,
      quality_deterministic: true,
      quality_judge: true,
      quality_note: "ok",
    });
  });
});

// --- CSV_COLUMNS -----------------------------------------------------------

describe("CSV_COLUMNS", () => {
  it("includes the judge column", () => {
    expect(CSV_COLUMNS).toContain("judge");
  });

  it("is an immutable tuple", () => {
    expect(Object.isFrozen(CSV_COLUMNS)).toBe(true);
  });
});

// --- writeJSON / writeCSV / writeReport ------------------------------------

describe("writeJSON", () => {
  it("writes JSON with the judge field", () => {
    const dir = mkdtempSync(join(tmpdir(), "report-"));
    const file = join(dir, "report.json");
    writeJSON(_rows(), file);
    const data = read(file);
    expect(file.endsWith(".json")).toBe(true);
    expect(data).toContain('"judge"');
    expect(data).toContain('"quality_passed"');
  });
});

describe("writeCSV", () => {
  it("writes CSV with the header row", () => {
    const dir = mkdtempSync(join(tmpdir(), "report-"));
    const file = join(dir, "report.csv");
    writeCSV(_rows(), file);
    const text = read(file);
    expect(text.startsWith("engine,model,")).toBe(true);
    const lines = text.split("\n").filter(Boolean);
    expect(lines.length).toBe(3); // header + 2 rows
    expect(lines[0]).toBe(CSV_COLUMNS.join(","));
  });

  it("writes quality booleans as text", () => {
    const dir = mkdtempSync(join(tmpdir(), "report-"));
    const file = join(dir, "report.csv");
    writeCSV(_rows(), file);
    const lines = read(file).split("\n").filter(Boolean);
    // First data row keeps the judge value.
    const row0 = lines[1];
    expect(row0).toContain("judge");
    // Quality booleans are written as lowercase text (TS String(true)).
    expect(row0).toContain("true");
  });
});

describe("writeReport", () => {
  it("dispatches by format", () => {
    const dir = mkdtempSync(join(tmpdir(), "report-"));
    const jsonPath = join(dir, "r.json");
    writeReport(_rows(), jsonPath, "json");
    expect(read(jsonPath).startsWith("[")).toBe(true);

    const csvPath = join(dir, "r.csv");
    writeReport(_rows(), csvPath, "csv");
    expect(read(csvPath).startsWith("engine,model,")).toBe(true);
  });
});

// --- printSummary ----------------------------------------------------------

describe("printSummary", () => {
  it("prints a friendly message for empty rows", () => {
    expect(() => printSummary([])).not.toThrow();
  });

  it("aggregates engines, rows, and pass counts", () => {
    const rows = _rows();
    printSummary(rows);
    const out = printSummary(rows);
    expect(out).toContain("engine-a");
    expect(out).toContain("rows:         2");
    expect(out).toContain("quality_passed:   1/2");
    expect(out).toContain("deterministic:    1/2");
  });

  it("lists judges", () => {
    const rows = [
      rowToObject({
        engine: "e",
        model: "m",
        judge: "gpt",
        task_id: "t",
        category: "qa",
      } as Row),
    ];
    expect(printSummary(rows)).toContain("judges:       gpt");
  });
});
