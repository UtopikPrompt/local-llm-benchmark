// A minimal async semaphore used to throttle concurrency.

export class Semaphore {
  #maxConcurrent: number;
  #available: number;
  #queue: Array<() => void> = [];
  #busy: boolean = false;

  constructor(maxConcurrent: number) {
    this.#maxConcurrent = maxConcurrent;
    this.#available = maxConcurrent;
  }

  withAcquired<T>(task: () => Promise<T>): Promise<T> {
    if (this.#available > 0) {
      this.#available -= 1;
      this.#busy = true;
      return this.#run(task);
    }
    return new Promise<T>((resolve) => {
      this.#queue.push(() => {
        this.#available += 1;
        if (this.#busy) {
          this.#busy = false;
        }
        resolve(task());
      });
    });
  }

  #run<T>(task: () => Promise<T>): Promise<T> {
    return task()
      .finally(() => {
        this.#busy = false;
        this.#available += 1;
        const next = this.#queue.shift();
        if (next) {
          next();
        }
      })
      .catch((error: unknown) => {
        this.#busy = false;
        this.#available += 1;
        const next = this.#queue.shift();
        if (next) {
          next();
        }
        throw error;
      });
  }
}
