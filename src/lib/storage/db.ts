// IndexedDB-backed persistence for results, engines, models, and corpus config.
// Thin wrapper over the `idb` promise-based DB so the rest of the app talks to
// IndexedDB without dealing with the sync API.

import { openDB, type IDBPDatabase } from "idb";

const DB_NAME = "local-llm-benchmark";
const DB_VERSION = 3;

interface Stores {
  rows: "rows";
  engines: "engines";
  judges: "judges";
  models: "models";
  tasks: "tasks";
  corpus: "corpus";
  params: "params";
}

type StoreName = keyof Stores;

// Per-store schema. Values are `unknown`; the concrete value type for each store
// lives in storage/index.ts, which casts the results when loading.
type StoresSchema = {
  [StoreName in keyof Stores]: {
    key: IDBValidKey;
    value: unknown;
  };
};

const STORES = {
  rows: "rows",
  engines: "engines",
  judges: "judges",
  models: "models",
  tasks: "tasks",
  corpus: "corpus",
  params: "params",
} as const;

let dbPromise: Promise<IDBPDatabase<StoresSchema>> | null = null;

async function openDatabase(): Promise<IDBPDatabase<StoresSchema>> {
  if (typeof indexedDB === "undefined") {
    throw new Error(
      "IndexedDB is not available. Persistence requires a browser. " +
        "(The `idb` library depends on the browser IndexedDB API.)",
    );
  }
  if (!dbPromise) {
    dbPromise = openDB<StoresSchema>(DB_NAME, DB_VERSION, {
      upgrade(database) {
        for (const store of Object.values(STORES)) {
          if (!database.objectStoreNames.contains(store)) {
            database.createObjectStore(store);
          }
        }
      },
    });
  }
  return dbPromise;
}

export async function put(
  store: StoreName,
  key: number | string,
  value: unknown,
): Promise<void> {
  await openDatabase().then((db) => db.put(store, value, key));
}

export async function get(
  store: StoreName,
  key: number | string,
): Promise<unknown> {
  const db = await openDatabase();
  return db.get(store, key);
}

export async function getAll(store: StoreName): Promise<unknown[]> {
  const db = await openDatabase();
  return db.getAll(store);
}

export async function deleteStore(store: StoreName): Promise<void> {
  const db = await openDatabase();
  db.deleteObjectStore(store);
}

export const storeNames = Object.values(STORES) as StoreName[];
