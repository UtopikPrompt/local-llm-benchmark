// IndexedDB-backed persistence for results, engines, models, and corpus config.
// Thin wrapper over the `idb` promise-based DB so the rest of the app talks to
// IndexedDB without dealing with the sync API.

import {
	openDB,
	type OpenDBDatabase,
	type OpenDBObjectStoreNames,
	type OpenDBValue,
} from 'idb';

const DB_NAME = 'local-llm-benchmark';
const DB_VERSION = 1;
const STORES = {
	rows: 'rows',
	engines: 'engines',
	judges: 'judges',
	models: 'models',
	corpus: 'corpus',
} as const;

let dbPromise: Promise<OpenDBDatabase> | null = null;

async function openDatabase(): Promise<OpenDBDatabase> {
	if (!dbPromise) {
		dbPromise = openDB<OpenDBValue, OpenDBObjectStoreNames<OpenDBValue>>(
			DB_NAME,
			DB_VERSION,
			{
				upgrade(db) {
					for (const store of Object.values(STORES)) {
						if (!db.objectStoreNames.contains(store)) {
							db.createObjectStore(store);
						}
					}
				},
			},
		);
	}
	return dbPromise;
}

export async function put(
	store: keyof typeof STORES,
	key: number | string,
	value: OpenDBValue,
): Promise<void> {
	await openDatabase().then((db) => db.put(store, value, key));
}

export async function get(
	store: keyof typeof STORES,
	key: number | string,
): Promise<OpenDBValue | undefined> {
	const db = await openDatabase();
	return db.get(store, key);
}

export async function getAll<T = OpenDBValue>(
	store: keyof typeof STORES,
): Promise<T[]> {
	const db = await openDatabase();
	return (await db.getAll<T>(store)) as T[];
}

export async function deleteStore(store: keyof typeof STORES): Promise<void> {
	const db = await openDatabase();
	await db.deleteObjectStore(store);
}

export const storeNames = Object.values(STORES);
