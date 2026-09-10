import '@testing-library/svelte';
import { cleanup } from '@testing-library/svelte';
import { afterEach } from 'vitest';

afterEach(() => {
	cleanup();
});
