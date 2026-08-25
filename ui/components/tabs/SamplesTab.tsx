"use client";

interface SamplesTabProps {
  onTry: (question: string) => void;
}

const SAMPLES = [
  {
    category: "Protein & Muscle",
    color: "text-primary",
    questions: [
      "How much protein do I need to build muscle?",
      "Does the timing of protein intake matter for muscle synthesis?",
      "Is whey protein better than plant protein for muscle building?",
      "What is the maximum amount of protein the body can absorb per meal?",
    ],
  },
  {
    category: "Creatine & Supplements",
    color: "text-accent",
    questions: [
      "Does creatine help with strength and power output?",
      "Is creatine monohydrate safe for long-term use?",
      "What does research say about NMN supplementation?",
      "Does beta-alanine improve athletic performance?",
    ],
  },
  {
    category: "Fat Loss & Nutrition",
    color: "text-primary",
    questions: [
      "What is the most effective diet for fat loss?",
      "Does intermittent fasting improve metabolic health?",
      "How does dietary fat intake affect hormone levels?",
      "What role does fibre play in weight management?",
    ],
  },
  {
    category: "Recovery & Sleep",
    color: "text-accent",
    questions: [
      "How does sleep deprivation affect muscle recovery?",
      "What is the recommended magnesium intake for athletes?",
      "Does cold water immersion speed up muscle recovery?",
      "How does cortisol affect muscle breakdown?",
    ],
  },
  {
    category: "Exercise Science",
    color: "text-primary",
    questions: [
      "Which exercises are most effective for building glutes?",
      "How many sets per week are optimal for hypertrophy?",
      "Is cardio harmful to muscle growth?",
      "What is the best rep range for building strength vs size?",
    ],
  },
];

export function SamplesTab({ onTry }: SamplesTabProps) {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold">Sample questions</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Click any question to load it into the Ask tab.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {SAMPLES.map((group) => (
          <div key={group.category} className="rounded-xl border border-border bg-card p-5 space-y-3">
            <h3 className={`text-xs font-semibold uppercase tracking-widest ${group.color}`}>
              {group.category}
            </h3>
            <ul className="space-y-2">
              {group.questions.map((q) => (
                <li key={q}>
                  <button
                    onClick={() => onTry(q)}
                    className="w-full text-left text-sm text-foreground/80 hover:text-foreground hover:bg-muted/40 rounded-md px-2 py-1.5 transition-colors"
                  >
                    {q}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
