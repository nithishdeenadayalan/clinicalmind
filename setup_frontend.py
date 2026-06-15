from pathlib import Path

base = Path("C:/full time/clinicalmind/frontend/src")

# Create directories
(base / "api").mkdir(exist_ok=True)
(base / "components").mkdir(exist_ok=True)

files = {}

files["api/client.ts"] = """import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

export interface TrialResult {
  nct_id: string;
  title: string;
  status_clean: string;
  phase_clean: string;
  conditions: string;
  interventions: string;
  sponsor: string;
  sponsor_class: string;
  countries: string;
  enrollment: string;
  is_high_value: string;
  score: number;
  rag_text: string;
}

export interface SearchResponse {
  query: string;
  total_results: number;
  results: TrialResult[];
}

export interface IntelligenceResponse {
  query: string;
  answer: string;
  sources: string[];
}

export const searchTrials = async (
  query: string,
  top_k: number = 10
): Promise<SearchResponse> => {
  const res = await api.post("/search/", { query, top_k });
  return res.data;
};

export const getIntelligence = async (
  query: string
): Promise<IntelligenceResponse> => {
  const res = await api.post("/intelligence/", { query });
  return res.data;
};
"""

files["components/TrialCard.tsx"] = """import { TrialResult } from "../api/client";

interface Props {
  trial: TrialResult;
  rank: number;
}

const statusColor: Record<string, string> = {
  Completed: "bg-green-100 text-green-800",
  Recruiting: "bg-blue-100 text-blue-800",
  Active: "bg-yellow-100 text-yellow-800",
  Terminated: "bg-red-100 text-red-800",
  Withdrawn: "bg-gray-100 text-gray-600",
};

export default function TrialCard({ trial, rank }: Props) {
  const status = trial.status_clean || "Unknown";
  const colorClass = statusColor[status] || "bg-gray-100 text-gray-600";
  const isHighValue = trial.is_high_value === "True";

  return (
    <div className={["bg-white rounded-lg border p-5", isHighValue ? "border-indigo-300 shadow-sm" : "border-gray-200"].join(" ")}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-gray-400">#{rank}</span>
            
              href={"https://clinicaltrials.gov/study/" + trial.nct_id}
              target="_blank"
              rel="noreferrer"
              className="text-xs font-mono text-indigo-600 hover:underline"
            >
              {trial.nct_id}
            </a>
            {isHighValue && (
              <span className="text-xs bg-indigo-50 text-indigo-700 border border-indigo-200 rounded px-1.5 py-0.5 font-medium">
                High Value
              </span>
            )}
          </div>
          <h3 className="text-sm font-semibold text-gray-900 leading-snug mb-2">
            {trial.title}
          </h3>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className={["rounded-full px-2.5 py-0.5 font-medium", colorClass].join(" ")}>
              {status}
            </span>
            {trial.phase_clean && trial.phase_clean !== "Not Specified" && (
              <span className="rounded-full px-2.5 py-0.5 bg-purple-100 text-purple-800 font-medium">
                {trial.phase_clean}
              </span>
            )}
            {trial.enrollment && trial.enrollment !== "nan" && (
              <span className="rounded-full px-2.5 py-0.5 bg-gray-100 text-gray-700">
                {"n=" + trial.enrollment}
              </span>
            )}
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className="text-lg font-bold text-indigo-600">
            {(trial.score * 100).toFixed(0)}
          </div>
          <div className="text-xs text-gray-400">score</div>
        </div>
      </div>
      {trial.conditions && (
        <div className="mt-3 text-xs text-gray-600">
          <span className="font-medium text-gray-700">Conditions: </span>
          {trial.conditions.split(";").slice(0, 3).join(", ")}
        </div>
      )}
      {trial.interventions && trial.interventions !== "nan" && (
        <div className="mt-1 text-xs text-gray-600">
          <span className="font-medium text-gray-700">Interventions: </span>
          {trial.interventions.split(";").slice(0, 3).join(", ")}
        </div>
      )}
      {trial.sponsor && (
        <div className="mt-1 text-xs text-gray-500">
          <span className="font-medium">Sponsor: </span>
          {trial.sponsor + " · " + trial.countries}
        </div>
      )}
    </div>
  );
}
"""

files["components/IntelligencePanel.tsx"] = """interface Props {
  query: string;
  answer: string;
  sources: string[];
  loading: boolean;
}

export default function IntelligencePanel({ query, answer, sources, loading }: Props) {
  if (loading) {
    return (
      <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-5 animate-pulse">
        <div className="h-4 bg-indigo-200 rounded w-1/3 mb-3"></div>
        <div className="space-y-2">
          <div className="h-3 bg-indigo-100 rounded"></div>
          <div className="h-3 bg-indigo-100 rounded w-5/6"></div>
          <div className="h-3 bg-indigo-100 rounded w-4/6"></div>
        </div>
      </div>
    );
  }

  if (!answer) return null;

  return (
    <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-5">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-2 h-2 rounded-full bg-indigo-500"></div>
        <span className="text-xs font-semibold text-indigo-700 uppercase tracking-wide">
          ClinicalMind Intelligence
        </span>
      </div>
      <p className="text-xs text-indigo-600 mb-3 italic">{query}</p>
      <div className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">
        {answer}
      </div>
      {sources.length > 0 && (
        <div className="mt-4 pt-3 border-t border-indigo-200">
          <p className="text-xs text-gray-500 font-medium mb-1">Sources</p>
          <div className="flex flex-wrap gap-1.5">
            {sources.map((s) => (
              
                key={s}
                href={"https://clinicaltrials.gov/study/" + s}
                target="_blank"
                rel="noreferrer"
                className="text-xs font-mono text-indigo-600 hover:underline"
              >
                {s}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
"""

files["App.tsx"] = """import { useState } from "react";
import { searchTrials, getIntelligence, TrialResult, IntelligenceResponse } from "./api/client";
import TrialCard from "./components/TrialCard";
import IntelligencePanel from "./components/IntelligencePanel";

const EXAMPLE_QUERIES = [
  "Phase 3 lung cancer immunotherapy",
  "GLP-1 diabetes weight loss recruiting",
  "Alzheimer prevention older adults NIH",
  "CAR-T cell therapy blood cancer completed",
];

export default function App() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<TrialResult[]>([]);
  const [intelligence, setIntelligence] = useState<IntelligenceResponse | null>(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [error, setError] = useState("");
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (q?: string) => {
    const searchQuery = q || query;
    if (!searchQuery.trim()) return;
    setQuery(searchQuery);
    setError("");
    setIntelligence(null);
    setSearchLoading(true);
    setAiLoading(true);
    setHasSearched(true);
    try {
      const searchRes = await searchTrials(searchQuery, 10);
      setResults(searchRes.results);
      setSearchLoading(false);
      const aiRes = await getIntelligence(searchQuery);
      setIntelligence(aiRes);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Something went wrong.");
    } finally {
      setSearchLoading(false);
      setAiLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">ClinicalMind</h1>
            <p className="text-xs text-gray-500">Clinical Trial Intelligence Platform</p>
          </div>
          <div className="text-xs text-gray-400">271,954 trials indexed</div>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-6 py-8">
        <div className="mb-8">
          <div className="flex gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Search 271,954 clinical trials..."
              className="flex-1 border border-gray-300 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
            <button
              onClick={() => handleSearch()}
              disabled={searchLoading}
              className="bg-indigo-600 text-white px-6 py-3 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {searchLoading ? "Searching..." : "Search"}
            </button>
          </div>
          {!hasSearched && (
            <div className="mt-3 flex flex-wrap gap-2">
              {EXAMPLE_QUERIES.map((q) => (
                <button
                  key={q}
                  onClick={() => handleSearch(q)}
                  className="text-xs text-indigo-600 bg-indigo-50 border border-indigo-200 rounded-full px-3 py-1 hover:bg-indigo-100 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          )}
        </div>
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
            {error}
          </div>
        )}
        {hasSearched && (
          <div className="space-y-6">
            <IntelligencePanel
              query={query}
              answer={intelligence?.answer || ""}
              sources={intelligence?.sources || []}
              loading={aiLoading}
            />
            <div>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-gray-700">
                  {searchLoading ? "Searching..." : (results.length + " results")}
                </h2>
              </div>
              {searchLoading ? (
                <div className="space-y-3">
                  {[0,1,2,3,4].map((i) => (
                    <div key={i} className="bg-white border border-gray-200 rounded-lg p-5 animate-pulse">
                      <div className="h-3 bg-gray-200 rounded w-1/4 mb-3"></div>
                      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                      <div className="h-3 bg-gray-100 rounded w-1/2"></div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-3">
                  {results.map((trial, i) => (
                    <TrialCard key={trial.nct_id} trial={trial} rank={i + 1} />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
        {!hasSearched && (
          <div className="text-center py-16 text-gray-400">
            <p className="text-sm">Search for clinical trials or ask an intelligence question</p>
          </div>
        )}
      </main>
    </div>
  );
}
"""

files["index.css"] = """@tailwind base;
@tailwind components;
@tailwind utilities;
"""

for relative_path, content in files.items():
    full_path = base / relative_path
    full_path.write_text(content, encoding="utf-8")
    print("Written:", full_path)

print("\nAll files written successfully.")