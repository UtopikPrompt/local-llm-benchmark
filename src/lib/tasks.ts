// Task definition: a single prompt the benchmark asks an engine to answer.
export interface Task {
  id: string;
  category: string;
  prompt: string;
  system: string | null;
  expected: string | null;
  validate: TaskValidator | null;
}

export type TaskValidator = (solution: string) => boolean;

// A Judge scores answers. `score` runs the engine for the judge and returns
// whether the answer was agreed plus a human-readable reason.
export interface Judge {
	name: string;
	score(task: Task, answer: string): Promise<{ agreed: boolean; note: string }>;
}
