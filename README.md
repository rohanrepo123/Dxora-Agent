# Website Link Analysis API

A synchronous FastAPI service that reads a public business website with Playwright and returns a structured marketing and SEO report. It uses LangGraph for the collect → analyze flow, LangChain for structured output, and Groq's `openai/gpt-oss-120b` model. Code is split into the requested `app/` package with services, schemas, validation utilities, and a small test suite.

## API

The assignment API has one application endpoint:

```http
POST /link-analysis
Content-Type: application/json
```

Request:

```json
{
  "url": "https://www.python.org/",
  "max_pages": 3
}
```

`max_pages` is optional and may be from 1 to 3. The response contains the brand summary, competitor suggestions, five platform-specific search queries, SEO improvements, cited services, target audiences, source URLs, and measured request metrics. Swagger documentation is available at `/docs`.

The service reads the home page and up to two relevant same-site product, service, solution, or about pages. It makes one Groq model call per request. It does not expose a public benchmark endpoint; model comparisons below are historical experiments recorded before the deployment version was restricted to Groq.

## Setup

Python 3.11 or newer is recommended.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

Set `GROQ_API_KEY` in your environment. For local development, create a `.env` beside `app.py`:

```env
GROQ_API_KEY=your_groq_api_key
```

Run locally:

```sh
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Never commit `.env` or API keys.

## Deployment on Render

This repository includes `render.yaml` for a Render Python web service. Connect the GitHub repository in Render, create the service from the Blueprint, and set `GROQ_API_KEY` in the service's environment variables. The start command binds to Render's `$PORT` and the build installs Chromium and its system dependencies.

The service writes request measurements to `metrics.csv`. Render's default filesystem is ephemeral, so those live additions may be lost when the instance restarts or redeploys. The committed CSV is the historical experiment snapshot used for the table below.

## Model experiments

The following are averages from the 16 successful historical rows currently in `metrics.csv`. The comparisons used the same application pipeline but multiple providers and models. These measurements are observational, not a controlled quality benchmark. Accuracy and competitor relevance were not independently scored; the quote-match column counts returned offerings whose evidence quote matched the collected source text. Cost is the CSV's estimated USD amount per successful request, not a provider invoice.

| Provider / model | Successful runs | Avg. latency (s) | Avg. input tokens | Avg. output tokens | Avg. estimated cost (USD) | Avg. quote-matched services |
|---|---:|---:|---:|---:|---:|---:|
| Groq `openai/gpt-oss-120b` | 6 | 6.61 | 3,869 | 2,144 | 0.00186695 | 2.00 |
| Groq `openai/gpt-oss-20b` | 1 | 3.31 | 1,946 | 753 | 0.00074370 | 0.00 |
| OpenAI `gpt-4.1-mini` | 3 | 8.66 | 3,169 | 895 | 0.00101260 | 1.67 |
| OpenAI `gpt-4o-mini` | 3 | 26.84 | 4,275 | 1,259 | 0.00139645 | 2.33 |
| OpenRouter `nvidia/nemotron-3.5-super-vl:free` | 3 | 21.38 | 1,392 | 3,056 | 0.00000000 | 0.00 |

JSON validity in this table is implicit: all listed rows were successful, schema-validated endpoint responses. These runs do not establish model accuracy. The small and uneven sample sizes, websites, provider load, and changing model prices limit direct comparisons. Refer to `metrics.csv` for the individual records.

## Implementation notes

- Playwright uses a synchronous browser session and reads at most three public pages.
- LangGraph runs the page collection node before the report generation node.
- Pydantic validates the request and generated report structure.
- Request timing, token usage, content size, quote matches, and estimated cost are appended to `metrics.csv`.
- Competitor strengths and gaps are AI hypotheses and require independent verification.
- Website fetches are restricted to public addresses, validated redirects, standard HTTP(S) ports, and bounded response sizes.

