import { useState, useMemo, useCallback, useEffect } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import type { RAGSearchResult } from "../lib/api";
import { createNoteAndProcess } from "../lib/dataPipeline";
import {
  Search, ChevronDown, ChevronRight, Copy, Check, Key,
  Zap, Palette, Code2, BarChart3, MessageSquare, Target, PenTool,
  ExternalLink, Star, Clock, Cpu, Settings2, Brain, FileText, Save,
  Loader, X,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface AITool {
  id: string;
  name: string;
  category: string;
  icon: string;
  description: string;
  promptTemplate: string;
  tokenTips: string;
  bestModel: string;
  connected: boolean;
  configKey: string;
}

type CategoryKey =
  | "ai-assistants"
  | "design-creative"
  | "development"
  | "data-analytics"
  | "communication"
  | "productivity"
  | "content-marketing";

/* ------------------------------------------------------------------ */
/*  Tool Data — 7 categories, 8-10 tools each                         */
/* ------------------------------------------------------------------ */

const CATEGORIES: { key: CategoryKey; label: string; icon: React.ReactNode }[] = [
  { key: "ai-assistants",    label: "AI Assistants",       icon: <Cpu size={18} /> },
  { key: "design-creative",  label: "Design & Creative",   icon: <Palette size={18} /> },
  { key: "development",      label: "Development",         icon: <Code2 size={18} /> },
  { key: "data-analytics",   label: "Data & Analytics",    icon: <BarChart3 size={18} /> },
  { key: "communication",    label: "Communication",       icon: <MessageSquare size={18} /> },
  { key: "productivity",     label: "Productivity",        icon: <Target size={18} /> },
  { key: "content-marketing",label: "Content & Marketing", icon: <PenTool size={18} /> },
];

const ALL_TOOLS: AITool[] = [
  /* ---- AI Assistants ---- */
  {
    id: "claude",
    name: "Claude (Anthropic)",
    category: "ai-assistants",
    icon: "C",
    description: "Advanced reasoning, code generation, and long-context analysis with up to 200K token windows.",
    promptTemplate: `You are an expert analyst. Given the following notes from my knowledge base, identify key themes, suggest connections I might have missed, and propose 3 actionable next steps.\n\nNotes:\n{context}\n\nPlease structure your response with: 1) Key Themes, 2) Hidden Connections, 3) Action Items.`,
    tokenTips: "Use XML tags to structure input sections. Claude excels with <instructions>, <context>, <examples> blocks. Trim whitespace from pasted content to save tokens.",
    bestModel: "Claude 3.5 Sonnet for code & analysis, Opus for complex multi-step reasoning",
    connected: false,
    configKey: "ANTHROPIC_API_KEY",
  },
  {
    id: "openai",
    name: "OpenAI / ChatGPT",
    category: "ai-assistants",
    icon: "O",
    description: "GPT-4o multimodal model for text, vision, and audio tasks with function calling support.",
    promptTemplate: `You are a senior technical writer. Rewrite the following draft to be clear, concise, and well-structured. Maintain the original meaning but improve readability. Use active voice and short paragraphs.\n\nDraft:\n{content}\n\nReturn the improved version followed by a bulleted list of changes you made.`,
    tokenTips: "Use system messages for persistent instructions. Prefer gpt-4o-mini for simple classification tasks to reduce cost by ~10x. Set max_tokens to cap runaway responses.",
    bestModel: "GPT-4o for complex reasoning & multimodal, GPT-4o-mini for classification & extraction",
    connected: false,
    configKey: "OPENAI_API_KEY",
  },
  {
    id: "gemini",
    name: "Google Gemini",
    category: "ai-assistants",
    icon: "G",
    description: "Multimodal AI with native image, video, and audio understanding. 1M+ token context window.",
    promptTemplate: `Analyze the attached image and provide:\n1. A detailed description of what you see\n2. Any text or data visible in the image\n3. Key insights or observations\n4. Suggested follow-up actions based on the content\n\nImage: {image_url}\nAdditional context: {context}`,
    tokenTips: "Leverage the massive 1M context window for entire codebases. Use Gemini Flash for latency-sensitive tasks. Batch multiple images in one request to save overhead.",
    bestModel: "Gemini 1.5 Pro for multimodal & long context, Gemini Flash for speed-critical tasks",
    connected: false,
    configKey: "GOOGLE_AI_API_KEY",
  },
  {
    id: "perplexity",
    name: "Perplexity",
    category: "ai-assistants",
    icon: "P",
    description: "AI-powered search engine with real-time web access and citation-backed answers.",
    promptTemplate: `Research the following topic and provide a comprehensive summary with citations. Focus on the most recent developments (last 6 months). Include competing perspectives where relevant.\n\nTopic: {query}\n\nFormat: Summary paragraph, then bulleted key findings with [source] citations.`,
    tokenTips: "Use the sonar-medium model for quick factual lookups. Reserve sonar-large for deep research. Include date constraints in your query to get fresher results.",
    bestModel: "Sonar Large for deep research, Sonar Medium for quick factual queries",
    connected: false,
    configKey: "PERPLEXITY_API_KEY",
  },
  {
    id: "mistral",
    name: "Mistral AI",
    category: "ai-assistants",
    icon: "M",
    description: "Open-weight models with strong multilingual capabilities and efficient inference.",
    promptTemplate: `[INST] You are a multilingual assistant. Translate the following text into {target_language}, preserving tone, idioms, and cultural nuances. Then provide a brief cultural context note for any phrases that don't translate directly.\n\nText: {text} [/INST]`,
    tokenTips: "Use Mistral Small for straightforward tasks. The Mixtral MoE architecture activates only relevant experts, keeping costs low. Use [INST] tags for better instruction following.",
    bestModel: "Mistral Large for complex tasks, Mistral Small for cost-efficient everyday use",
    connected: false,
    configKey: "MISTRAL_API_KEY",
  },
  {
    id: "cohere",
    name: "Cohere",
    category: "ai-assistants",
    icon: "Co",
    description: "Enterprise-focused NLP with best-in-class RAG, embeddings, and reranking capabilities.",
    promptTemplate: `Using the following documents as context, answer the user's question. Cite specific documents using [Doc N] notation. If the answer isn't in the documents, say so explicitly.\n\nDocuments:\n{documents}\n\nQuestion: {question}\n\nProvide a concise answer with citations, then list confidence score (0-1).`,
    tokenTips: "Use Cohere's native rerank API before generation to improve RAG quality and reduce context tokens. Embed API supports batch processing for cost savings.",
    bestModel: "Command R+ for RAG & enterprise tasks, Embed v3 for semantic search",
    connected: false,
    configKey: "COHERE_API_KEY",
  },
  {
    id: "ollama",
    name: "Meta Llama (via Ollama)",
    category: "ai-assistants",
    icon: "L",
    description: "Run Llama 3.1, Mistral, and other open models locally. Zero API costs, full data privacy.",
    promptTemplate: `<|begin_of_text|><|start_header_id|>system<|end_header_id|>\nYou are a helpful coding assistant running locally. Analyze the code below for bugs, security issues, and performance improvements. Be specific about line numbers.\n<|start_header_id|>user<|end_header_id|>\n{code}\n<|start_header_id|>assistant<|end_header_id|>`,
    tokenTips: "Use quantized models (Q4_K_M) for 4x memory savings with minimal quality loss. Run llama3.1:8b for fast iteration, llama3.1:70b for production quality. Keep context under 8K for best speed.",
    bestModel: "Llama 3.1 70B for quality, Llama 3.1 8B for speed, runs 100% local",
    connected: false,
    configKey: "OLLAMA_BASE_URL",
  },
  {
    id: "deepseek",
    name: "DeepSeek",
    category: "ai-assistants",
    icon: "D",
    description: "State-of-the-art coding model with exceptional performance on math and reasoning benchmarks.",
    promptTemplate: `You are an expert software engineer. Given the following requirements, write production-ready code with:\n1. Proper error handling and edge cases\n2. Type safety and input validation\n3. Unit test examples\n4. Brief inline documentation\n\nRequirements: {requirements}\nLanguage: {language}\nFramework: {framework}`,
    tokenTips: "DeepSeek-Coder-V2 is optimized for code tasks at a fraction of GPT-4 cost. Use fill-in-the-middle format for code completion. Batch related code questions together.",
    bestModel: "DeepSeek-V2.5 for general, DeepSeek-Coder-V2 for programming tasks",
    connected: false,
    configKey: "DEEPSEEK_API_KEY",
  },

  /* ---- Design & Creative ---- */
  {
    id: "canva",
    name: "Canva AI",
    category: "design-creative",
    icon: "Ca",
    description: "AI-powered design platform for presentations, social media graphics, and brand assets.",
    promptTemplate: `Create a {format} design with the following specifications:\n- Topic: {topic}\n- Brand colors: {colors}\n- Style: {style} (e.g., minimal, bold, corporate)\n- Key message: {message}\n- Include: {elements}\n\nEnsure the design follows accessibility guidelines with sufficient contrast ratios.`,
    tokenTips: "Use Magic Design for quick iterations. Specify exact dimensions to avoid regeneration. Reference existing brand kit templates to reduce prompt complexity.",
    bestModel: "Canva Magic Design for templates, Magic Write for copy generation",
    connected: false,
    configKey: "CANVA_API_KEY",
  },
  {
    id: "figma",
    name: "Figma AI",
    category: "design-creative",
    icon: "Fi",
    description: "Collaborative design tool with AI-powered auto-layout, prototyping, and design system management.",
    promptTemplate: `Generate a Figma component specification:\n- Component: {component_name}\n- Variants: {variants}\n- Props: {props}\n- Responsive breakpoints: mobile (375px), tablet (768px), desktop (1440px)\n- Design tokens: {tokens}\n\nInclude auto-layout settings, padding values, and interaction states (default, hover, active, disabled).`,
    tokenTips: "Use Figma's native AI features for layout suggestions. Export design tokens as JSON to reduce manual prompt specification. Use component sets for variant generation.",
    bestModel: "Figma AI native for layout, pair with Claude for design system documentation",
    connected: false,
    configKey: "FIGMA_API_KEY",
  },
  {
    id: "midjourney",
    name: "Midjourney",
    category: "design-creative",
    icon: "Mj",
    description: "Premium AI image generation known for artistic quality, photorealism, and consistent style.",
    promptTemplate: `{subject}, {style} style, {lighting} lighting, {composition} composition, {color_palette} color palette, {mood} mood, shot on {camera}, {additional_details} --ar {aspect_ratio} --v 6 --s {stylize_value} --q 2`,
    tokenTips: "Use --s (stylize) values: 0-250 for photorealistic, 250-750 for balanced, 750+ for artistic. Add --no to exclude unwanted elements. Use /describe on reference images to learn effective prompt patterns.",
    bestModel: "Midjourney v6 for photorealism, Niji for anime/illustration styles",
    connected: false,
    configKey: "MIDJOURNEY_API_KEY",
  },
  {
    id: "dalle",
    name: "DALL-E 3",
    category: "design-creative",
    icon: "DE",
    description: "OpenAI's image generation model with excellent text rendering and prompt adherence.",
    promptTemplate: `Generate an image: {description}\n\nStyle: {style}\nComposition: {composition}\nText to include (if any): "{text_overlay}"\nColor scheme: {colors}\nMood: {mood}\n\nIMPORTANT: The image should be suitable for {use_case} and maintain a {tone} tone.`,
    tokenTips: "DALL-E 3 auto-rewrites prompts for better results. Use the 'revised_prompt' field to learn what works. Standard quality (1024x1024) costs half of HD. Batch requests with asyncio.",
    bestModel: "DALL-E 3 for text-in-image, quality illustrations, and prompt fidelity",
    connected: false,
    configKey: "OPENAI_API_KEY",
  },
  {
    id: "stable-diffusion",
    name: "Stable Diffusion",
    category: "design-creative",
    icon: "SD",
    description: "Open-source image generation with fine-tuning support, ControlNet, and local deployment.",
    promptTemplate: `Positive prompt: {subject}, {details}, {style}, {quality_tags}\nNegative prompt: blurry, low quality, distorted, deformed, watermark, text\n\nSettings:\n- Steps: 30\n- CFG Scale: 7.5\n- Sampler: DPM++ 2M Karras\n- Seed: {seed}\n- Model: {checkpoint}`,
    tokenTips: "Use LoRA models for consistent characters/styles at minimal VRAM cost. ControlNet with depth/canny maps gives precise composition control. Run SDXL Turbo for 1-step generation in prototyping.",
    bestModel: "SDXL for quality, SD Turbo for speed, fine-tuned checkpoints for specific styles",
    connected: false,
    configKey: "STABILITY_API_KEY",
  },
  {
    id: "adobe-firefly",
    name: "Adobe Firefly",
    category: "design-creative",
    icon: "Af",
    description: "Commercially safe AI generation trained only on licensed content. Integrated across Adobe Creative Cloud.",
    promptTemplate: `Generate a commercially-safe image for {use_case}:\n- Subject: {subject}\n- Style reference: {style_reference}\n- Content type: {type} (photo / illustration / 3D)\n- Aspect ratio: {ratio}\n- Effects: {effects}\n\nThis will be used in {context}, so ensure it's appropriate for commercial use.`,
    tokenTips: "Firefly credits vary by operation: text-to-image uses 1 credit, generative fill uses 1 per edit. Use Structure Reference for consistent outputs. Batch similar generations to reuse style settings.",
    bestModel: "Firefly 3 for photorealism, Firefly Vector for scalable graphics",
    connected: false,
    configKey: "ADOBE_API_KEY",
  },
  {
    id: "runway",
    name: "Runway Gen-3",
    category: "design-creative",
    icon: "Rw",
    description: "AI video generation and editing. Text-to-video, image-to-video, and motion brush tools.",
    promptTemplate: `Generate a {duration}-second video:\n- Scene description: {scene}\n- Camera movement: {camera_motion} (e.g., slow dolly in, pan left, static)\n- Style: {style}\n- Mood/atmosphere: {mood}\n- Starting frame: {start_image_url}\n\nThe video should transition smoothly and maintain visual coherence throughout.`,
    tokenTips: "Start with 4-second clips and extend. Use image-to-video for more control than text-to-video. Motion Brush lets you specify exactly which elements move. Gen-3 Alpha Turbo is 7x faster at lower cost.",
    bestModel: "Gen-3 Alpha for quality, Gen-3 Alpha Turbo for speed and iteration",
    connected: false,
    configKey: "RUNWAY_API_KEY",
  },
  {
    id: "luma",
    name: "Luma AI",
    category: "design-creative",
    icon: "Lu",
    description: "Photorealistic 3D capture and AI video generation with Dream Machine for cinematic clips.",
    promptTemplate: `Create a cinematic video clip:\n- Scene: {scene_description}\n- Duration: {duration} seconds\n- Camera: {camera_movement}\n- Lighting: {lighting_style}\n- Reference image (optional): {reference}\n\nMaintain photorealistic quality with smooth motion and natural physics.`,
    tokenTips: "Use keyframe images for start and end frames to control output precisely. Dream Machine excels at natural motion and physics. Lower resolution previews cost fewer credits for iteration.",
    bestModel: "Dream Machine for video, Luma 3D for photogrammetry and 3D capture",
    connected: false,
    configKey: "LUMA_API_KEY",
  },

  /* ---- Development ---- */
  {
    id: "github-copilot",
    name: "GitHub Copilot",
    category: "development",
    icon: "GH",
    description: "AI pair programmer integrated into VS Code, JetBrains, and Neovim. Context-aware code completion.",
    promptTemplate: `// Task: {task_description}\n// Language: {language}\n// Framework: {framework}\n// Requirements:\n// - {requirement_1}\n// - {requirement_2}\n// - {requirement_3}\n// \n// Related files: {related_files}\n// Tests should cover: {test_cases}\n\n{function_signature}`,
    tokenTips: "Open relevant files in adjacent tabs for better context. Use specific function signatures and JSDoc/docstring comments as prompts. Copilot Chat supports @workspace for repo-wide context.",
    bestModel: "Copilot with GPT-4o for complex generation, standard Copilot for completions",
    connected: false,
    configKey: "GITHUB_TOKEN",
  },
  {
    id: "cursor",
    name: "Cursor",
    category: "development",
    icon: "Cu",
    description: "AI-first code editor with Composer for multi-file edits, codebase-wide context, and chat.",
    promptTemplate: `@codebase Refactor the {module} module to:\n1. Extract {function} into a separate utility\n2. Add proper TypeScript types for all parameters\n3. Implement error boundaries with custom error classes\n4. Add JSDoc documentation\n5. Write unit tests with >90% coverage\n\nMaintain backward compatibility with existing API consumers.`,
    tokenTips: "Use @codebase for repo-wide context and @file to reference specific files. Composer mode handles multi-file refactors. Use .cursorrules for project-specific AI instructions. Cmd+K for inline edits.",
    bestModel: "Claude 3.5 Sonnet via Cursor for code, GPT-4o for general chat",
    connected: false,
    configKey: "CURSOR_API_KEY",
  },
  {
    id: "replit",
    name: "Replit AI",
    category: "development",
    icon: "Re",
    description: "Cloud IDE with AI agent that can build, debug, and deploy full-stack applications from prompts.",
    promptTemplate: `Build a {app_type} application with the following specifications:\n- Frontend: {frontend_framework}\n- Backend: {backend_framework}\n- Database: {database}\n- Authentication: {auth_method}\n- Key features: {features}\n\nInclude proper error handling, input validation, and a clean UI. Deploy-ready configuration.`,
    tokenTips: "Replit Agent works best with clear, specific feature descriptions. Break complex apps into phases. Use the built-in database for prototypes to avoid external dependency setup time.",
    bestModel: "Replit Agent for full-stack builds, Replit AI Chat for debugging",
    connected: false,
    configKey: "REPLIT_API_KEY",
  },
  {
    id: "supabase",
    name: "Supabase",
    category: "development",
    icon: "Sb",
    description: "Open-source Firebase alternative with PostgreSQL, auth, storage, edge functions, and vector embeddings.",
    promptTemplate: `Design a Supabase schema for {project}:\n\nTables needed:\n{table_definitions}\n\nRow Level Security policies:\n- {rls_policy_1}\n- {rls_policy_2}\n\nEdge Functions:\n- {function_1}: {function_1_description}\n\nGenerate SQL migrations, RLS policies, and TypeScript types.`,
    tokenTips: "Use Supabase's AI SQL editor for schema generation. Generate TypeScript types automatically with 'supabase gen types'. Use pgvector extension for embeddings to avoid separate vector DB costs.",
    bestModel: "Supabase AI assistant for SQL, pair with Claude for complex RLS policies",
    connected: false,
    configKey: "SUPABASE_API_KEY",
  },
  {
    id: "vercel",
    name: "Vercel",
    category: "development",
    icon: "Ve",
    description: "Frontend deployment platform with v0 AI for generating React components and full-stack Next.js apps.",
    promptTemplate: `Create a Next.js component using v0:\n- Component: {component_name}\n- Description: {description}\n- Styling: Tailwind CSS with {theme} theme\n- Interactivity: {interactions}\n- Responsive: mobile-first\n- Accessibility: WCAG 2.1 AA compliant\n\nUse shadcn/ui components where applicable. Include loading and error states.`,
    tokenTips: "v0 generates shadcn/ui components by default. Specify 'use server' or 'use client' directives. Vercel AI SDK handles streaming responses efficiently. Use Edge Runtime for lower latency.",
    bestModel: "v0 for component generation, Vercel AI SDK for LLM app development",
    connected: false,
    configKey: "VERCEL_API_KEY",
  },
  {
    id: "netlify",
    name: "Netlify",
    category: "development",
    icon: "Nt",
    description: "Web deployment with serverless functions, edge compute, and integrated CI/CD pipelines.",
    promptTemplate: `Configure Netlify deployment for {project}:\n\nBuild settings:\n- Build command: {build_cmd}\n- Publish directory: {publish_dir}\n- Node version: {node_version}\n\nServerless functions:\n{functions_list}\n\nEnvironment variables:\n{env_vars}\n\nRedirects and headers:\n{redirects}`,
    tokenTips: "Use Netlify Functions for API routes without a separate backend. Edge Functions run in <50ms. Use netlify.toml for configuration-as-code. Blob storage for key-value data avoids database costs.",
    bestModel: "Pair with Claude for serverless function logic and deployment configs",
    connected: false,
    configKey: "NETLIFY_API_KEY",
  },
  {
    id: "railway",
    name: "Railway",
    category: "development",
    icon: "Ry",
    description: "Infrastructure platform for deploying backend services, databases, and cron jobs with zero config.",
    promptTemplate: `Deploy a {service_type} service on Railway:\n\nService config:\n- Runtime: {runtime}\n- Start command: {start_cmd}\n- Health check: {health_endpoint}\n\nDatabases needed:\n{databases}\n\nEnvironment variables:\n{env_vars}\n\nCron jobs:\n{cron_schedules}\n\nScaling: {scaling_config}`,
    tokenTips: "Railway auto-detects Dockerfiles and Nixpacks configs. Use Railway's template marketplace for common stacks. Shared variables across services reduce config duplication. Use sleep schedules for dev environments.",
    bestModel: "Pair with GPT-4o for Dockerfile optimization and infrastructure decisions",
    connected: false,
    configKey: "RAILWAY_API_KEY",
  },
  {
    id: "planetscale",
    name: "PlanetScale",
    category: "development",
    icon: "PS",
    description: "Serverless MySQL-compatible database with branching, non-blocking schema changes, and query insights.",
    promptTemplate: `Design a PlanetScale database schema:\n\nTables:\n{table_definitions}\n\nIndexes for common queries:\n{query_patterns}\n\nBranch strategy:\n- main: production\n- develop: staging\n- feature/{feature}: feature branches\n\nGenerate DDL statements compatible with PlanetScale (no foreign key constraints).`,
    tokenTips: "PlanetScale doesn't support foreign keys; enforce referential integrity in application code. Use deploy requests for safe schema migrations. Query Insights identifies slow queries automatically.",
    bestModel: "Claude 3.5 for schema design, PlanetScale Insights for query optimization",
    connected: false,
    configKey: "PLANETSCALE_API_KEY",
  },

  /* ---- Data & Analytics ---- */
  {
    id: "notion-ai",
    name: "Notion AI",
    category: "data-analytics",
    icon: "No",
    description: "AI writing and analysis built into Notion workspaces. Summarize pages, generate content, and query databases.",
    promptTemplate: `Analyze the following Notion database and provide insights:\n\nDatabase: {database_name}\nFields: {fields}\nFilters: {filters}\nDate range: {date_range}\n\nGenerate:\n1. Summary statistics\n2. Trend analysis\n3. Anomaly detection\n4. Recommended actions\n5. A formatted table of key findings`,
    tokenTips: "Use Notion's native AI for in-context summaries. API pagination defaults to 100 items; use start_cursor for large databases. Filter server-side rather than fetching all records.",
    bestModel: "Notion AI native for workspace tasks, API + Claude for advanced analysis",
    connected: false,
    configKey: "NOTION_API_KEY",
  },
  {
    id: "airtable",
    name: "Airtable",
    category: "data-analytics",
    icon: "At",
    description: "Spreadsheet-database hybrid with automations, interfaces, and AI-powered field suggestions.",
    promptTemplate: `Query Airtable base {base_id}:\n\nTable: {table_name}\nFilter: {filter_formula}\nSort: {sort_field} {sort_direction}\nFields to return: {fields}\n\nTransform the results:\n1. Group by {group_field}\n2. Calculate {aggregation} for each group\n3. Format as {output_format}\n4. Highlight records where {condition}`,
    tokenTips: "Use filterByFormula server-side to reduce payload size. Airtable's API rate limit is 5 req/sec; implement exponential backoff. Use field IDs instead of names for stable integrations.",
    bestModel: "GPT-4o for formula generation, Airtable Extensions for native AI features",
    connected: false,
    configKey: "AIRTABLE_API_KEY",
  },
  {
    id: "tableau",
    name: "Tableau",
    category: "data-analytics",
    icon: "Tb",
    description: "Enterprise data visualization platform with AI-driven analytics, natural language queries, and dashboards.",
    promptTemplate: `Create a Tableau dashboard specification:\n\nData source: {data_source}\nKey metrics: {metrics}\nDimensions: {dimensions}\nFilters: {filters}\n\nVisualization requirements:\n1. {chart_1_type}: showing {chart_1_data}\n2. {chart_2_type}: showing {chart_2_data}\n3. {chart_3_type}: showing {chart_3_data}\n\nInteractivity: cross-filtering between charts, date range selector, drill-down capability.`,
    tokenTips: "Use Tableau Pulse for AI-generated metric summaries. Extract calculations let you pre-compute expensive metrics. Use context filters before dimension filters for better query performance.",
    bestModel: "Tableau Ask Data for NL queries, pair with GPT-4o for calculated field formulas",
    connected: false,
    configKey: "TABLEAU_API_KEY",
  },
  {
    id: "retool",
    name: "Retool",
    category: "data-analytics",
    icon: "Rt",
    description: "Low-code platform for building internal tools. Connect databases, APIs, and AI models with drag-and-drop UI.",
    promptTemplate: `Build a Retool internal tool:\n\nPurpose: {purpose}\nData sources: {data_sources}\nUser roles: {roles}\n\nUI Components:\n{component_list}\n\nQueries:\n{query_definitions}\n\nWorkflows:\n{workflow_steps}\n\nAccess control: {permissions}`,
    tokenTips: "Use Retool AI to generate SQL queries from natural language. Prepared statements prevent SQL injection. Use transformers for data shaping instead of complex queries. Cache expensive queries with a 5-min TTL.",
    bestModel: "Retool AI for query generation, pair with Claude for complex business logic",
    connected: false,
    configKey: "RETOOL_API_KEY",
  },
  {
    id: "amplitude",
    name: "Amplitude",
    category: "data-analytics",
    icon: "Am",
    description: "Product analytics platform with behavioral cohorts, funnel analysis, and AI-powered insights.",
    promptTemplate: `Analyze user behavior in Amplitude:\n\nEvent: {event_name}\nUser segment: {segment}\nDate range: {date_range}\n\nAnalysis required:\n1. Funnel conversion: {funnel_steps}\n2. Retention curve: {retention_event}\n3. User path analysis from {start_event} to {end_event}\n4. Statistical significance of {experiment}\n\nProvide actionable recommendations to improve {target_metric} by {target_percentage}%.`,
    tokenTips: "Use Amplitude's chart API to export analysis data. Group-by properties are cheaper than user-level queries. Use behavioral cohorts to pre-filter users before complex analyses.",
    bestModel: "Amplitude AI for anomaly detection, pair with GPT-4o for insight narratives",
    connected: false,
    configKey: "AMPLITUDE_API_KEY",
  },
  {
    id: "mixpanel",
    name: "Mixpanel",
    category: "data-analytics",
    icon: "Mx",
    description: "Event-based analytics with real-time dashboards, cohort analysis, and predictive modeling.",
    promptTemplate: `Generate a Mixpanel report:\n\nInsight type: {insight_type} (funnel / retention / flows / trends)\nEvents: {events}\nProperties to break down by: {properties}\nDate range: {date_range}\nSegments: {user_segments}\n\nGoal: Identify why {metric} has {changed_direction} by {percentage}% this {time_period}.\nSuggest 3 hypotheses and how to validate each.`,
    tokenTips: "Use JQL (JavaScript Query Language) for complex custom queries. Mixpanel's Spark AI translates natural language to reports. Limit property cardinality to <1000 unique values for performant breakdowns.",
    bestModel: "Mixpanel Spark for NL queries, pair with Claude for statistical analysis",
    connected: false,
    configKey: "MIXPANEL_API_KEY",
  },
  {
    id: "segment",
    name: "Segment",
    category: "data-analytics",
    icon: "Sg",
    description: "Customer data platform for collecting, cleaning, and routing event data to 400+ downstream tools.",
    promptTemplate: `Design a Segment tracking plan:\n\nProduct: {product_name}\nKey user flows: {user_flows}\n\nEvents to track:\n{event_definitions}\n\nIdentify calls:\n- Traits: {user_traits}\n- Group traits: {group_traits}\n\nDestinations:\n{destination_configs}\n\nData governance rules:\n{pii_handling}`,
    tokenTips: "Use Protocols for schema enforcement to prevent dirty data. Replay API lets you resend historical events to new destinations. Use Functions for custom transformations without separate infrastructure.",
    bestModel: "Pair with Claude for tracking plan design, GPT-4o for transformation functions",
    connected: false,
    configKey: "SEGMENT_API_KEY",
  },

  /* ---- Communication ---- */
  {
    id: "slack",
    name: "Slack",
    category: "communication",
    icon: "Sl",
    description: "Team communication with AI-powered search, channel summaries, and workflow builder integrations.",
    promptTemplate: `Create a Slack bot message for {channel}:\n\nPurpose: {purpose}\nTrigger: {trigger_event}\n\nMessage blocks:\n- Header: {header_text}\n- Section: {body_text}\n- Fields: {field_key_values}\n- Actions: {button_labels}\n\nThread follow-up: {follow_up_message}\n\nFormat using Block Kit JSON.`,
    tokenTips: "Use Block Kit for rich messages instead of plain text. conversations.history has a 200-message default limit; paginate for threads. Use socket mode for real-time events without public URLs.",
    bestModel: "Slack AI for channel summaries, pair with Claude for bot logic",
    connected: false,
    configKey: "SLACK_BOT_TOKEN",
  },
  {
    id: "discord",
    name: "Discord",
    category: "communication",
    icon: "Dc",
    description: "Community platform with bot framework, slash commands, forums, and voice channels.",
    promptTemplate: `Build a Discord bot command:\n\nCommand: /{command_name}\nDescription: {description}\nOptions: {options_with_types}\n\nBehavior:\n1. {step_1}\n2. {step_2}\n3. {step_3}\n\nResponse format:\nEmbed:\n- Title: {embed_title}\n- Color: {embed_color}\n- Fields: {embed_fields}\n- Footer: {embed_footer}`,
    tokenTips: "Use interaction-based bots (slash commands) over message content intent for better rate limits. Discord.js v14 supports autocomplete. Defer replies for operations >3 seconds to avoid timeout.",
    bestModel: "Claude for complex bot logic, GPT-4o-mini for simple command responses",
    connected: false,
    configKey: "DISCORD_BOT_TOKEN",
  },
  {
    id: "telegram",
    name: "Telegram",
    category: "communication",
    icon: "Tg",
    description: "Messaging platform with powerful Bot API, inline keyboards, web apps, and group management.",
    promptTemplate: `Create a Telegram bot flow:\n\nBot purpose: {purpose}\nCommands:\n/start - {start_description}\n/help - {help_description}\n/{custom_cmd} - {custom_description}\n\nConversation flow:\n{flow_steps}\n\nInline keyboard options:\n{keyboard_layout}\n\nCallback query handlers:\n{callback_handlers}`,
    tokenTips: "Use webhooks instead of polling for production. InlineKeyboardMarkup for interactive menus. Telegram supports long messages up to 4096 chars. Use reply_markup for structured user inputs.",
    bestModel: "Any model works; Claude for conversational bots, GPT-4o-mini for simple handlers",
    connected: false,
    configKey: "TELEGRAM_BOT_TOKEN",
  },
  {
    id: "whatsapp",
    name: "WhatsApp Business API",
    category: "communication",
    icon: "WA",
    description: "Business messaging with template messages, interactive lists, product catalogs, and payment integration.",
    promptTemplate: `Design a WhatsApp Business flow:\n\nBusiness: {business_name}\nUse case: {use_case}\n\nMessage templates (require approval):\n1. Welcome: {welcome_template}\n2. Order update: {order_template}\n3. Support: {support_template}\n\nInteractive elements:\n- Quick replies: {quick_replies}\n- List message: {list_sections}\n- CTA buttons: {cta_buttons}\n\nEscalation path: {escalation_flow}`,
    tokenTips: "Template messages must be pre-approved by Meta. Use session messages (24h window) for free-form replies. Interactive lists support up to 10 sections with 10 rows each. Media messages are separate API calls.",
    bestModel: "Claude for conversation design, GPT-4o for template copywriting",
    connected: false,
    configKey: "WHATSAPP_API_KEY",
  },
  {
    id: "twilio",
    name: "Twilio",
    category: "communication",
    icon: "Tw",
    description: "Cloud communications API for SMS, voice, video, and email. Programmable messaging with AI integration.",
    promptTemplate: `Build a Twilio communication flow:\n\nChannel: {channel} (SMS / Voice / WhatsApp)\nTrigger: {trigger}\n\nFlow steps:\n1. Receive {inbound_type}\n2. Process with AI: {ai_processing}\n3. Respond with: {response_template}\n4. If {condition}, escalate to {escalation}\n\nTwiML/Studio flow:\n{flow_definition}\n\nError handling: {error_strategy}`,
    tokenTips: "Use Twilio Functions for serverless handlers. Studio for visual flow building. SMS segments are 160 chars (GSM-7) or 70 chars (Unicode); keep messages concise. Use messaging services for automatic sender rotation.",
    bestModel: "Twilio AI Assistants for voice, pair with Claude for complex routing logic",
    connected: false,
    configKey: "TWILIO_API_KEY",
  },
  {
    id: "sendgrid",
    name: "SendGrid",
    category: "communication",
    icon: "SG",
    description: "Transactional and marketing email API with dynamic templates, analytics, and deliverability tools.",
    promptTemplate: `Create a SendGrid email campaign:\n\nFrom: {sender_name} <{sender_email}>\nTemplate: {template_name}\n\nDynamic content:\n- Subject lines (A/B): {subject_a} | {subject_b}\n- Preheader: {preheader}\n- Personalization: {merge_fields}\n\nSegment: {recipient_segment}\nSchedule: {send_time}\n\nTracking:\n- Open tracking: enabled\n- Click tracking: enabled\n- UTM params: {utm_params}`,
    tokenTips: "Use dynamic templates with Handlebars for personalization. Batch API sends up to 1000 recipients per request. Use suppression groups for unsubscribe management. Pre-warm new IPs gradually.",
    bestModel: "GPT-4o for email copywriting, Claude for template logic and Handlebars",
    connected: false,
    configKey: "SENDGRID_API_KEY",
  },

  /* ---- Productivity ---- */
  {
    id: "linear",
    name: "Linear",
    category: "productivity",
    icon: "Li",
    description: "Modern issue tracker with AI triage, automatic prioritization, cycles, and roadmap planning.",
    promptTemplate: `Create a Linear issue:\n\nTitle: {title}\nDescription:\n## Context\n{context}\n\n## Acceptance Criteria\n- [ ] {criteria_1}\n- [ ] {criteria_2}\n- [ ] {criteria_3}\n\n## Technical Notes\n{technical_notes}\n\nLabels: {labels}\nPriority: {priority}\nEstimate: {estimate}\nProject: {project}\nCycle: {cycle}`,
    tokenTips: "Use Linear's AI features for auto-triage and duplicate detection. GraphQL API is more efficient than REST for batch operations. Use webhooks for real-time sync instead of polling.",
    bestModel: "Linear AI for triage, pair with Claude for detailed spec writing",
    connected: false,
    configKey: "LINEAR_API_KEY",
  },
  {
    id: "jira",
    name: "Jira",
    category: "productivity",
    icon: "Ji",
    description: "Enterprise project management with Atlassian Intelligence, advanced workflows, and DevOps integrations.",
    promptTemplate: `Create a Jira issue with the following:\n\nProject: {project_key}\nType: {issue_type}\nSummary: {summary}\n\nDescription:\nh2. Overview\n{overview}\n\nh2. Requirements\n{requirements}\n\nh2. Definition of Done\n* {dod_1}\n* {dod_2}\n\nComponents: {components}\nFix Version: {version}\nStory Points: {points}\nSprint: {sprint}`,
    tokenTips: "Use JQL for precise queries: 'project = X AND status changed AFTER -7d'. Bulk operations API for batch updates. Atlassian Intelligence summarizes issues and suggests related tickets.",
    bestModel: "Atlassian Intelligence for summaries, Claude for requirements decomposition",
    connected: false,
    configKey: "JIRA_API_KEY",
  },
  {
    id: "asana",
    name: "Asana",
    category: "productivity",
    icon: "As",
    description: "Work management platform with AI status updates, goals tracking, portfolios, and workflow automation.",
    promptTemplate: `Create an Asana project plan:\n\nProject: {project_name}\nGoal: {goal}\nTimeline: {start_date} to {end_date}\n\nSections:\n{sections_with_tasks}\n\nMilestones:\n{milestones}\n\nDependencies:\n{task_dependencies}\n\nCustom fields:\n- Priority: {priority_options}\n- Status: {status_options}\n- Owner: {team_members}`,
    tokenTips: "Use Asana's batch API to create multiple tasks in one request. Opt_fields parameter reduces response payload. Use webhooks with X-Hook-Secret for secure real-time updates.",
    bestModel: "Asana Intelligence for status summaries, pair with GPT-4o for project planning",
    connected: false,
    configKey: "ASANA_API_KEY",
  },
  {
    id: "monday",
    name: "Monday.com",
    category: "productivity",
    icon: "Mn",
    description: "Work OS with AI assistant, customizable workflows, dashboards, and 200+ integrations.",
    promptTemplate: `Design a Monday.com board:\n\nBoard name: {board_name}\nPurpose: {purpose}\n\nColumns:\n{column_definitions}\n\nGroups:\n{group_names}\n\nAutomations:\nWhen {trigger}, then {action}\n\nDashboard widgets:\n{widget_configs}\n\nIntegrations:\n{integration_list}`,
    tokenTips: "Use Monday's GraphQL API with complexity budgets. Queries have a complexity limit of 10M per minute. Use column_values_str for faster reads. Batch mutations with a single API call.",
    bestModel: "Monday AI for status reporting, pair with Claude for automation design",
    connected: false,
    configKey: "MONDAY_API_KEY",
  },
  {
    id: "trello",
    name: "Trello",
    category: "productivity",
    icon: "Tr",
    description: "Visual Kanban boards with Butler automation, Power-Ups, and Atlassian Intelligence integration.",
    promptTemplate: `Set up a Trello board workflow:\n\nBoard: {board_name}\nLists: {list_names}\n\nCard template:\n- Title: {card_title_format}\n- Description: {card_description_template}\n- Labels: {label_colors_and_names}\n- Checklist: {checklist_items}\n- Due date rule: {due_date_logic}\n\nButler automations:\n{automation_rules}`,
    tokenTips: "Use batch endpoints for bulk card creation. Butler rules are free and reduce API calls. Use label colors as a lightweight categorization system. Webhooks for board changes are more efficient than polling.",
    bestModel: "Atlassian Intelligence for card summaries, GPT-4o for Butler rule design",
    connected: false,
    configKey: "TRELLO_API_KEY",
  },
  {
    id: "clickup",
    name: "ClickUp",
    category: "productivity",
    icon: "CU",
    description: "All-in-one productivity platform with AI writing, docs, whiteboards, time tracking, and goal management.",
    promptTemplate: `Create a ClickUp workspace structure:\n\nSpace: {space_name}\nFolders:\n{folder_structure}\n\nTask template:\n- Name: {task_name_pattern}\n- Custom fields: {custom_fields}\n- Priority levels: {priorities}\n- Time estimate: {estimate_formula}\n\nGoals:\n{goal_definitions}\n\nAutomations:\n{automation_triggers}`,
    tokenTips: "Use ClickUp's AI to generate task descriptions and summaries. API rate limit is 100 req/min for free, 10,000 for enterprise. Use custom task IDs for stable references across integrations.",
    bestModel: "ClickUp AI for task writing, pair with Claude for complex workflow design",
    connected: false,
    configKey: "CLICKUP_API_KEY",
  },
  {
    id: "todoist",
    name: "Todoist",
    category: "productivity",
    icon: "Td",
    description: "Smart task manager with natural language input, AI task suggestions, and GTD-style organization.",
    promptTemplate: `Organize tasks in Todoist using GTD methodology:\n\nInbox items to process:\n{inbox_items}\n\nCategorize each into:\n- Projects: {project_list}\n- Contexts: @{context_labels}\n- Priority: p1 (urgent) to p4 (someday)\n- Due dates: natural language (e.g., "every Monday at 9am")\n- Labels: {label_taxonomy}\n\nGenerate Todoist-compatible natural language task strings.`,
    tokenTips: "Use natural language dates in the Sync API for flexible scheduling. Filters API supports complex queries. Batch sync endpoint processes up to 100 commands per request.",
    bestModel: "Any model for task parsing; Claude excels at GTD-style categorization",
    connected: false,
    configKey: "TODOIST_API_KEY",
  },

  /* ---- Content & Marketing ---- */
  {
    id: "jasper",
    name: "Jasper",
    category: "content-marketing",
    icon: "Ja",
    description: "Enterprise AI content platform with brand voice, campaigns, content briefs, and team collaboration.",
    promptTemplate: `Create marketing content with Jasper:\n\nBrand voice: {brand_voice_description}\nTone: {tone}\nAudience: {target_audience}\n\nContent type: {content_type}\nTopic: {topic}\nKeywords: {primary_keywords}\nWord count: {target_length}\n\nCTA: {call_to_action}\nBrand guidelines to follow:\n{guidelines}\n\nInclude: headline options (3), meta description, social snippets.`,
    tokenTips: "Use Jasper's Brand Voice feature to maintain consistency without repeating brand context. Templates reduce prompt tokens by 40%. Use Campaigns for multi-asset content batches.",
    bestModel: "Jasper native for brand-consistent copy, pair with GPT-4o for strategic messaging",
    connected: false,
    configKey: "JASPER_API_KEY",
  },
  {
    id: "copyai",
    name: "Copy.ai",
    category: "content-marketing",
    icon: "Cp",
    description: "AI copywriting with workflows for sales emails, ad copy, blog posts, and social media content.",
    promptTemplate: `Generate copy variations:\n\nProduct: {product_name}\nValue proposition: {value_prop}\nTarget persona: {persona}\nPain points: {pain_points}\n\nGenerate:\n1. 5 headline variations (max 60 chars each)\n2. 3 email subject lines\n3. 2 ad copy variants (primary text + headline + description)\n4. 1 landing page hero section\n\nTone: {tone}\nCTA: {cta}`,
    tokenTips: "Use Copy.ai workflows for multi-step content generation. Save brand infobase to avoid repeating product context. Batch similar content types together for consistent voice.",
    bestModel: "Copy.ai native for sales copy, pair with Claude for long-form content strategy",
    connected: false,
    configKey: "COPYAI_API_KEY",
  },
  {
    id: "writesonic",
    name: "Writesonic",
    category: "content-marketing",
    icon: "Ws",
    description: "AI writing assistant with Chatsonic (web-aware), article writer, and SEO-optimized content generation.",
    promptTemplate: `Write an SEO-optimized article:\n\nTopic: {topic}\nPrimary keyword: {primary_keyword}\nSecondary keywords: {secondary_keywords}\nSearch intent: {intent_type}\nTarget word count: {word_count}\n\nStructure:\n- Hook intro (problem statement)\n- {num_sections} H2 sections with H3 subsections\n- Practical examples\n- FAQ section (5 questions)\n- Conclusion with CTA\n\nReadability: Grade 8 level, short paragraphs, bullet points.`,
    tokenTips: "Use Chatsonic for real-time research before writing. Article Writer 6.0 handles long-form in one pass. Use the API's quality parameter to balance speed vs. output quality.",
    bestModel: "Writesonic for SEO content, Chatsonic for research-backed articles",
    connected: false,
    configKey: "WRITESONIC_API_KEY",
  },
  {
    id: "hubspot",
    name: "HubSpot",
    category: "content-marketing",
    icon: "HS",
    description: "CRM platform with AI content assistant, marketing automation, sales sequences, and analytics.",
    promptTemplate: `Create a HubSpot marketing automation workflow:\n\nGoal: {campaign_goal}\nSegment: {contact_segment}\n\nTrigger: {enrollment_trigger}\n\nWorkflow steps:\n1. Send email: {email_1_template}\n   Wait: {delay_1}\n2. If/then: {condition}\n   Yes branch: {yes_action}\n   No branch: {no_action}\n3. {additional_steps}\n\nGoal completion: {goal_criteria}\nSuppression: {suppression_list}\n\nReporting: track {metrics}`,
    tokenTips: "Use HubSpot's AI to generate email copy and subject lines. CRM object API supports batch reads of 100 records. Use association labels for typed relationships. Workflow delay actions reduce API polling.",
    bestModel: "HubSpot AI for CRM copy, pair with Claude for workflow logic and segmentation strategy",
    connected: false,
    configKey: "HUBSPOT_API_KEY",
  },
  {
    id: "mailchimp",
    name: "Mailchimp",
    category: "content-marketing",
    icon: "MC",
    description: "Email marketing platform with AI subject line helper, content optimizer, send time optimization, and automation.",
    promptTemplate: `Design a Mailchimp email campaign:\n\nCampaign: {campaign_name}\nAudience: {audience_segment}\n\nEmail content:\n- Subject: {subject_line} (A/B variant: {subject_alt})\n- Preview text: {preview_text}\n- Header image: {header_description}\n- Body: {body_sections}\n- CTA button: {cta_text} -> {cta_url}\n\nAutomation:\n- Trigger: {trigger}\n- Series: {email_series_count} emails over {duration}\n- Send time: optimized per subscriber timezone`,
    tokenTips: "Use Mailchimp's Creative Assistant for on-brand designs. Batch operations endpoint handles up to 500 operations. Use segments with AND/OR conditions for precise targeting. Pre-built automations save setup time.",
    bestModel: "Mailchimp AI for subject lines, pair with GPT-4o for email copy and strategy",
    connected: false,
    configKey: "MAILCHIMP_API_KEY",
  },
  {
    id: "buffer",
    name: "Buffer",
    category: "content-marketing",
    icon: "Bu",
    description: "Social media scheduling with AI assistant for caption writing, hashtag suggestions, and optimal timing.",
    promptTemplate: `Create a social media content calendar:\n\nBrand: {brand_name}\nPlatforms: {platforms}\nPosting frequency: {frequency_per_platform}\nTime period: {date_range}\n\nContent pillars:\n1. {pillar_1}: {description_1}\n2. {pillar_2}: {description_2}\n3. {pillar_3}: {description_3}\n\nFor each post generate:\n- Platform-optimized caption\n- Hashtag set (5-10)\n- Best posting time\n- Visual description for the creative team\n- Engagement prompt (question or CTA)`,
    tokenTips: "Use Buffer's AI Assistant for platform-specific caption adaptation. Schedule posts in batches using the publish API. Use Buffer Analytics to identify best performing content types and times.",
    bestModel: "Buffer AI for captions, pair with Claude for content strategy and calendar planning",
    connected: false,
    configKey: "BUFFER_API_KEY",
  },
  {
    id: "hootsuite",
    name: "Hootsuite",
    category: "content-marketing",
    icon: "Ht",
    description: "Social media management with OwlyWriter AI, social listening, analytics, and team approval workflows.",
    promptTemplate: `Plan a Hootsuite social campaign:\n\nCampaign: {campaign_name}\nObjective: {objective}\nPlatforms: {platforms}\n\nContent streams:\n{content_streams}\n\nScheduling rules:\n- Optimal times: auto-detect per platform\n- Frequency caps: {frequency_caps}\n- Approval workflow: {approval_chain}\n\nMonitoring:\n- Keywords: {monitoring_keywords}\n- Sentiment alerts: {sentiment_thresholds}\n- Competitor accounts: {competitor_handles}\n\nReporting: weekly {report_metrics}`,
    tokenTips: "OwlyWriter AI generates captions from URLs or prompts. Use streams for real-time monitoring instead of manual checks. Bulk Composer imports CSV files for mass scheduling. Use saved replies for common responses.",
    bestModel: "OwlyWriter AI for social copy, pair with Claude for strategy and sentiment analysis",
    connected: false,
    configKey: "HOOTSUITE_API_KEY",
  },
];

/* ------------------------------------------------------------------ */
/*  Helper: category icon map for badge rendering                      */
/* ------------------------------------------------------------------ */

const CATEGORY_MAP = Object.fromEntries(CATEGORIES.map((c) => [c.key, c]));

/* ------------------------------------------------------------------ */
/*  Section (accordion)                                                */
/* ------------------------------------------------------------------ */

function Section({
  icon,
  title,
  count,
  connectedCount,
  defaultOpen = false,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  count: number;
  connectedCount: number;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="ath-section">
      <button className="ath-section-header" onClick={() => setOpen((o) => !o)}>
        <span className="ath-section-icon">{icon}</span>
        <span className="ath-section-title">{title}</span>
        <span className="ath-section-count">
          {connectedCount > 0 && (
            <span className="ath-connected-badge">{connectedCount} connected</span>
          )}
          <span className="ath-total-badge">{count} tools</span>
        </span>
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </button>
      {open && <div className="ath-section-body">{children}</div>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tool Card                                                          */
/* ------------------------------------------------------------------ */

function ToolCard({
  tool,
  expanded,
  onToggle,
  onCopyPrompt,
  copiedId,
  onConfigure,
  configuringId,
  apiKeyDraft,
  onApiKeyChange,
  onApiKeySave,
  onUseWithContext,
}: {
  tool: AITool;
  expanded: boolean;
  onToggle: () => void;
  onCopyPrompt: (id: string, prompt: string) => void;
  copiedId: string | null;
  onConfigure: (id: string) => void;
  configuringId: string | null;
  apiKeyDraft: string;
  onApiKeyChange: (v: string) => void;
  onApiKeySave: (id: string, key: string) => void;
  onUseWithContext?: (toolId: string) => void;
}) {
  const isCopied = copiedId === tool.id;
  const isConfiguring = configuringId === tool.id;

  return (
    <div className={`ath-card ${expanded ? "ath-card-expanded" : ""}`}>
      {/* Header row */}
      <button className="ath-card-header" onClick={onToggle}>
        <span className="ath-card-icon-box">{tool.icon}</span>
        <div className="ath-card-info">
          <div className="ath-card-name-row">
            <span className="ath-card-name">{tool.name}</span>
            <span className={`ath-status-dot ${tool.connected ? "ath-dot-connected" : "ath-dot-disconnected"}`} />
          </div>
          <span className="ath-card-desc">{tool.description}</span>
        </div>
        <div className="ath-card-meta">
          <span className="ath-model-badge">
            <Cpu size={11} />
            {tool.bestModel.split(" for ")[0]}
          </span>
        </div>
        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="ath-card-detail">
          {/* Best model */}
          <div className="ath-detail-row">
            <Star size={14} />
            <div>
              <span className="ath-detail-label">Best Model</span>
              <span className="ath-detail-value">{tool.bestModel}</span>
            </div>
          </div>

          {/* Prompt template */}
          <div className="ath-detail-row">
            <Zap size={14} />
            <div className="ath-detail-full">
              <span className="ath-detail-label">Prompt Template</span>
              <div className="ath-prompt-block">
                <pre className="ath-prompt-pre">{tool.promptTemplate}</pre>
                <div style={{ display: "flex", gap: 6 }}>
                  <button
                    className="ath-copy-btn"
                    onClick={() => onCopyPrompt(tool.id, tool.promptTemplate)}
                    title="Copy prompt"
                  >
                    {isCopied ? <Check size={13} /> : <Copy size={13} />}
                    {isCopied ? "Copied!" : "Copy Prompt"}
                  </button>
                  {onUseWithContext && (
                    <button
                      className="ath-copy-btn"
                      onClick={() => onUseWithContext(tool.id)}
                      title="Search your notes and assemble context for this tool"
                      style={{ background: "rgba(139, 92, 246, 0.1)", color: "#8b5cf6", borderColor: "rgba(139, 92, 246, 0.3)" }}
                    >
                      <Brain size={13} />
                      Use with Context
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Token tips */}
          <div className="ath-detail-row">
            <Clock size={14} />
            <div>
              <span className="ath-detail-label">Token Optimization Tips</span>
              <span className="ath-detail-value">{tool.tokenTips}</span>
            </div>
          </div>

          {/* Configure / API key */}
          <div className="ath-detail-actions">
            {isConfiguring ? (
              <div className="ath-config-form">
                <Key size={14} />
                <input
                  className="ath-config-input"
                  type="password"
                  placeholder={`Enter ${tool.configKey}`}
                  value={apiKeyDraft}
                  onChange={(e) => onApiKeyChange(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") onApiKeySave(tool.id, apiKeyDraft);
                  }}
                />
                <button
                  className="ath-btn ath-btn-primary"
                  onClick={() => onApiKeySave(tool.id, apiKeyDraft)}
                >
                  Save
                </button>
                <button
                  className="ath-btn"
                  onClick={() => onConfigure("")}
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                className="ath-btn ath-btn-outline"
                onClick={() => onConfigure(tool.id)}
              >
                <Settings2 size={13} />
                {tool.connected ? "Reconfigure" : "Configure"}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export function AIToolsHub() {
  const { dispatch } = useApp();

  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<CategoryKey | "all">("all");
  const [expandedTool, setExpandedTool] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [configuringId, setConfiguringId] = useState<string | null>(null);
  const [apiKeyDraft, setApiKeyDraft] = useState("");
  const [connectedKeys, setConnectedKeys] = useState<Record<string, boolean>>({});

  /* ---- Context Assembly Mode ---- */
  const [contextMode, setContextMode] = useState(false);
  const [contextToolId, setContextToolId] = useState<string | null>(null);
  const [contextIntent, setContextIntent] = useState("");
  const [contextSearching, setContextSearching] = useState(false);
  const [contextResults, setContextResults] = useState<RAGSearchResult[]>([]);
  const [selectedContextIds, setSelectedContextIds] = useState<Set<string>>(new Set());
  const [assembledPrompt, setAssembledPrompt] = useState("");
  const [contextCopied, setContextCopied] = useState(false);

  // Check for context passed from other features (via sessionStorage)
  useEffect(() => {
    const stored = sessionStorage.getItem("einstein-ai-context");
    if (stored) {
      sessionStorage.removeItem("einstein-ai-context");
      try {
        const data = JSON.parse(stored);
        setContextMode(true);
        setContextIntent(data.content || "");
      } catch { /* ignore */ }
    }
  }, []);

  const handleOpenContextMode = useCallback((toolId: string) => {
    setContextMode(true);
    setContextToolId(toolId);
    setContextIntent("");
    setContextResults([]);
    setSelectedContextIds(new Set());
    setAssembledPrompt("");
  }, []);

  const handleContextSearch = useCallback(async () => {
    if (!contextIntent.trim()) return;
    setContextSearching(true);
    try {
      const results = await api.ragSearch(contextIntent, 8);
      setContextResults(results);
      // Auto-select top 3
      const autoSelect = new Set(results.slice(0, 3).map((r) => r.note_id));
      setSelectedContextIds(autoSelect);
    } catch {
      setContextResults([]);
    } finally {
      setContextSearching(false);
    }
  }, [contextIntent]);

  const toggleContextSelection = useCallback((noteId: string) => {
    setSelectedContextIds((prev) => {
      const next = new Set(prev);
      if (next.has(noteId)) next.delete(noteId);
      else next.add(noteId);
      return next;
    });
  }, []);

  const handleAssemblePrompt = useCallback(() => {
    const tool = ALL_TOOLS.find((t) => t.id === contextToolId);
    const template = tool?.promptTemplate || "Analyze the following context:\n\n{context}";

    const selectedNotes = contextResults.filter((r) => selectedContextIds.has(r.note_id));
    const contextBlock = selectedNotes
      .map((r) => `--- ${r.title} ---\n${r.chunk}`)
      .join("\n\n");

    const prompt = template
      .replace("{context}", contextBlock)
      .replace("{content}", contextBlock);

    setAssembledPrompt(prompt);
  }, [contextToolId, contextResults, selectedContextIds]);

  const handleCopyAssembled = useCallback(() => {
    navigator.clipboard.writeText(assembledPrompt).then(() => {
      setContextCopied(true);
      setTimeout(() => setContextCopied(false), 2000);
    });
  }, [assembledPrompt]);

  const handleSaveResponseAsNote = useCallback(async () => {
    const tool = ALL_TOOLS.find((t) => t.id === contextToolId);
    const title = `AI Response — ${tool?.name || "AI Tool"} — ${new Date().toISOString().slice(0, 10)}`;
    const content = `# ${title}\n\n## Prompt\n${assembledPrompt.slice(0, 500)}...\n\n## Response\n\n_Paste the AI response here after running the prompt._\n`;
    try {
      const result = await createNoteAndProcess(title, content, dispatch, {
        source: `ai-tool-${contextToolId}`,
      });
      dispatch({ type: "SET_ACTIVE_NOTE", id: result.note.id });
      dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
    } catch (err) {
      console.error("Failed to save AI response note:", err);
    }
  }, [contextToolId, assembledPrompt, dispatch]);

  /* Mark tools as connected based on saved keys */
  const tools = useMemo(() => {
    return ALL_TOOLS.map((t) => ({
      ...t,
      connected: connectedKeys[t.id] ?? t.connected,
    }));
  }, [connectedKeys]);

  /* Filter tools */
  const filteredTools = useMemo(() => {
    let result = tools;
    if (categoryFilter !== "all") {
      result = result.filter((t) => t.category === categoryFilter);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (t) =>
          t.name.toLowerCase().includes(q) ||
          t.description.toLowerCase().includes(q) ||
          t.bestModel.toLowerCase().includes(q) ||
          t.category.toLowerCase().includes(q)
      );
    }
    return result;
  }, [tools, categoryFilter, searchQuery]);

  /* Group by category */
  const grouped = useMemo(() => {
    const map: Record<string, AITool[]> = {};
    for (const t of filteredTools) {
      (map[t.category] ??= []).push(t);
    }
    return map;
  }, [filteredTools]);

  /* Stats */
  const totalCount = tools.length;
  const connectedCount = tools.filter((t) => t.connected).length;

  /* Handlers */
  const handleCopyPrompt = (id: string, prompt: string) => {
    navigator.clipboard.writeText(prompt).then(() => {
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 1800);
    });
  };

  const handleConfigure = (id: string) => {
    setConfiguringId(id || null);
    setApiKeyDraft("");
  };

  const handleApiKeySave = (id: string, _key: string) => {
    if (!_key.trim()) return;
    setConnectedKeys((prev) => ({ ...prev, [id]: true }));
    setConfiguringId(null);
    setApiKeyDraft("");
  };

  return (
    <div className="ath-root">
      <div className="ath-wrapper">
        {/* -------------------------------------------------------- */}
        {/*  Hero header                                              */}
        {/* -------------------------------------------------------- */}
        <div className="ath-hero">
          <Zap size={36} />
          <h1>AI Tools Hub</h1>
          <p>50+ AI integrations with optimized prompts</p>
          <div className="ath-stats-row">
            <span className="ath-stat">
              <span className="ath-stat-num">{totalCount}</span> tools
            </span>
            <span className="ath-stat-sep">/</span>
            <span className="ath-stat ath-stat-connected">
              <span className="ath-stat-num">{connectedCount}</span> connected
            </span>
          </div>
        </div>

        {/* -------------------------------------------------------- */}
        {/*  Context Assembly Panel                                    */}
        {/* -------------------------------------------------------- */}
        {contextMode && (
          <div className="ath-context-panel">
            <div className="ath-context-header">
              <Brain size={16} />
              <span>Context Assembly</span>
              <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                {contextToolId ? `for ${ALL_TOOLS.find(t => t.id === contextToolId)?.name || ""}` : ""}
              </span>
              <button className="ath-context-close" onClick={() => setContextMode(false)}>
                <X size={14} />
              </button>
            </div>

            {/* Step 1: What do you want to do? */}
            <div className="ath-context-step">
              <label>What do you want to do?</label>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  className="ath-context-input"
                  placeholder="e.g., Help me plan the product launch based on my meeting notes..."
                  value={contextIntent}
                  onChange={(e) => setContextIntent(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") handleContextSearch(); }}
                />
                <button
                  className="ath-context-search-btn"
                  onClick={handleContextSearch}
                  disabled={contextSearching || !contextIntent.trim()}
                >
                  {contextSearching ? <Loader size={14} className="ath-spin" /> : <Search size={14} />}
                  Search Notes
                </button>
              </div>
            </div>

            {/* Step 2: Select relevant notes */}
            {contextResults.length > 0 && (
              <div className="ath-context-step">
                <label>Select notes to include ({selectedContextIds.size} selected)</label>
                <div className="ath-context-results">
                  {contextResults.map((r) => (
                    <label key={r.note_id} className={`ath-context-result ${selectedContextIds.has(r.note_id) ? "selected" : ""}`}>
                      <input
                        type="checkbox"
                        checked={selectedContextIds.has(r.note_id)}
                        onChange={() => toggleContextSelection(r.note_id)}
                      />
                      <div className="ath-context-result-info">
                        <span className="ath-context-result-title">
                          <FileText size={12} /> {r.title}
                        </span>
                        <span className="ath-context-result-snippet">{r.chunk.slice(0, 120)}...</span>
                      </div>
                      <span className="ath-context-result-score">{Math.round(r.score * 100)}%</span>
                    </label>
                  ))}
                </div>
                <button
                  className="ath-context-search-btn"
                  onClick={handleAssemblePrompt}
                  disabled={selectedContextIds.size === 0}
                  style={{ alignSelf: "flex-start", marginTop: 8 }}
                >
                  <Zap size={14} />
                  Assemble Prompt
                </button>
              </div>
            )}

            {/* Step 3: Assembled prompt */}
            {assembledPrompt && (
              <div className="ath-context-step">
                <label>Assembled Prompt ({assembledPrompt.length} chars)</label>
                <textarea
                  className="ath-context-prompt"
                  value={assembledPrompt}
                  onChange={(e) => setAssembledPrompt(e.target.value)}
                  rows={8}
                />
                <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                  <button className="ath-context-search-btn" onClick={handleCopyAssembled}>
                    {contextCopied ? <Check size={14} /> : <Copy size={14} />}
                    {contextCopied ? "Copied!" : "Copy Prompt"}
                  </button>
                  <button
                    className="ath-context-search-btn"
                    onClick={handleSaveResponseAsNote}
                    style={{ background: "rgba(16, 185, 129, 0.15)", color: "#10b981", border: "1px solid rgba(16, 185, 129, 0.3)" }}
                  >
                    <Save size={14} />
                    Save Response as Note
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* -------------------------------------------------------- */}
        {/*  Search & filter bar                                      */}
        {/* -------------------------------------------------------- */}
        <div className="ath-filter-bar">
          <div className="ath-search-box">
            <Search size={16} />
            <input
              className="ath-search-input"
              placeholder="Search tools, models, categories..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="ath-category-filters">
            <button
              className={`ath-cat-btn ${categoryFilter === "all" ? "ath-cat-active" : ""}`}
              onClick={() => setCategoryFilter("all")}
            >
              All
            </button>
            {CATEGORIES.map((cat) => (
              <button
                key={cat.key}
                className={`ath-cat-btn ${categoryFilter === cat.key ? "ath-cat-active" : ""}`}
                onClick={() => setCategoryFilter(cat.key)}
              >
                {cat.icon}
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        {/* -------------------------------------------------------- */}
        {/*  Category sections                                        */}
        {/* -------------------------------------------------------- */}
        {filteredTools.length === 0 ? (
          <div className="ath-empty">
            <Search size={32} />
            <p>No tools match your search.</p>
          </div>
        ) : (
          CATEGORIES.filter((cat) => grouped[cat.key]?.length).map((cat) => {
            const catTools = grouped[cat.key]!;
            const catConnected = catTools.filter((t) => t.connected).length;
            return (
              <Section
                key={cat.key}
                icon={cat.icon}
                title={cat.label}
                count={catTools.length}
                connectedCount={catConnected}
                defaultOpen={categoryFilter !== "all" || catTools.length <= 8}
              >
                <div className="ath-cards-list">
                  {catTools.map((tool) => (
                    <ToolCard
                      key={tool.id}
                      tool={tool}
                      expanded={expandedTool === tool.id}
                      onToggle={() =>
                        setExpandedTool((prev) => (prev === tool.id ? null : tool.id))
                      }
                      onCopyPrompt={handleCopyPrompt}
                      copiedId={copiedId}
                      onConfigure={handleConfigure}
                      configuringId={configuringId}
                      apiKeyDraft={apiKeyDraft}
                      onApiKeyChange={setApiKeyDraft}
                      onApiKeySave={handleApiKeySave}
                      onUseWithContext={handleOpenContextMode}
                    />
                  ))}
                </div>
              </Section>
            );
          })
        )}

        <div className="ath-footer">
          <p>All prompt templates are customizable. Copy, adapt, and iterate for your workflow.</p>
        </div>
      </div>

      {/* -------------------------------------------------------------- */}
      {/*  Scoped styles                                                  */}
      {/* -------------------------------------------------------------- */}
      <style>{`
        .ath-root {
          height: 100%;
          overflow: auto;
          background: var(--bg-primary, #09090b);
        }
        .ath-wrapper {
          max-width: 860px;
          margin: 0 auto;
          padding: 24px 32px 64px;
        }

        /* Hero */
        .ath-hero {
          text-align: center;
          margin-bottom: 28px;
          padding: 28px 0 20px;
        }
        .ath-hero svg {
          color: var(--accent, #3b82f6);
        }
        .ath-hero h1 {
          font-size: 1.8rem;
          font-weight: 700;
          margin: 10px 0 4px;
          color: var(--text-primary, #e4e4e7);
        }
        .ath-hero p {
          color: var(--text-muted, #a1a1aa);
          font-size: 0.95rem;
          margin: 0;
        }
        .ath-stats-row {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          margin-top: 12px;
          font-size: 0.85rem;
        }
        .ath-stat {
          color: var(--text-muted, #a1a1aa);
        }
        .ath-stat-num {
          font-weight: 700;
          color: var(--text-primary, #e4e4e7);
        }
        .ath-stat-connected .ath-stat-num {
          color: #22c55e;
        }
        .ath-stat-sep {
          color: var(--border, #27272a);
        }

        /* Filter bar */
        .ath-filter-bar {
          margin-bottom: 20px;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .ath-search-box {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px 14px;
          border-radius: 10px;
          background: var(--bg-secondary, #18181b);
          border: 1px solid var(--border, #27272a);
        }
        .ath-search-box svg {
          color: var(--text-muted, #a1a1aa);
          flex-shrink: 0;
        }
        .ath-search-input {
          flex: 1;
          background: none;
          border: none;
          outline: none;
          color: var(--text-primary, #e4e4e7);
          font-size: 0.92rem;
        }
        .ath-search-input::placeholder {
          color: var(--text-muted, #52525b);
        }
        .ath-category-filters {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }
        .ath-cat-btn {
          display: flex;
          align-items: center;
          gap: 5px;
          padding: 6px 12px;
          border-radius: 8px;
          border: 1px solid var(--border, #27272a);
          background: var(--bg-secondary, #18181b);
          color: var(--text-muted, #a1a1aa);
          font-size: 0.8rem;
          cursor: pointer;
          transition: all 0.15s;
        }
        .ath-cat-btn:hover {
          border-color: var(--accent, #3b82f6);
          color: var(--text-primary, #e4e4e7);
        }
        .ath-cat-btn.ath-cat-active {
          background: var(--accent, #3b82f6);
          border-color: var(--accent, #3b82f6);
          color: #fff;
        }
        .ath-cat-btn svg {
          width: 14px;
          height: 14px;
        }

        /* Sections */
        .ath-section {
          border: 1px solid var(--border, #27272a);
          border-radius: 10px;
          margin-bottom: 12px;
          background: var(--bg-secondary, #18181b);
          overflow: hidden;
        }
        .ath-section-header {
          display: flex;
          align-items: center;
          gap: 10px;
          width: 100%;
          padding: 14px 18px;
          background: none;
          border: none;
          color: var(--text-primary, #e4e4e7);
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
        }
        .ath-section-header:hover {
          background: var(--bg-hover, #1f1f23);
        }
        .ath-section-header > svg {
          color: var(--text-muted, #a1a1aa);
          flex-shrink: 0;
          margin-left: auto;
        }
        .ath-section-icon {
          color: var(--accent, #3b82f6);
          display: flex;
        }
        .ath-section-title {
          flex: 1;
          text-align: left;
        }
        .ath-section-count {
          display: flex;
          gap: 8px;
          align-items: center;
          margin-right: 4px;
        }
        .ath-connected-badge {
          font-size: 0.72rem;
          font-weight: 500;
          padding: 2px 8px;
          border-radius: 9999px;
          background: rgba(34,197,94,0.15);
          color: #22c55e;
        }
        .ath-total-badge {
          font-size: 0.72rem;
          font-weight: 500;
          padding: 2px 8px;
          border-radius: 9999px;
          background: rgba(59,130,246,0.12);
          color: var(--accent, #3b82f6);
        }
        .ath-section-body {
          padding: 4px 18px 18px;
        }

        /* Cards list */
        .ath-cards-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        /* Card */
        .ath-card {
          border: 1px solid var(--border, #27272a);
          border-radius: 8px;
          overflow: hidden;
          background: var(--bg-primary, #09090b);
          transition: border-color 0.15s;
        }
        .ath-card:hover {
          border-color: #3f3f46;
        }
        .ath-card-expanded {
          border-color: var(--accent, #3b82f6);
        }
        .ath-card-header {
          display: flex;
          align-items: center;
          gap: 12px;
          width: 100%;
          padding: 12px 14px;
          background: none;
          border: none;
          color: var(--text-primary, #e4e4e7);
          cursor: pointer;
          text-align: left;
        }
        .ath-card-header:hover {
          background: var(--bg-hover, #1f1f23);
        }
        .ath-card-header > svg {
          color: var(--text-muted, #a1a1aa);
          flex-shrink: 0;
        }
        .ath-card-icon-box {
          width: 36px;
          height: 36px;
          border-radius: 8px;
          background: linear-gradient(135deg, rgba(59,130,246,0.15), rgba(139,92,246,0.15));
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          font-size: 0.8rem;
          color: var(--accent, #3b82f6);
          flex-shrink: 0;
        }
        .ath-card-info {
          flex: 1;
          min-width: 0;
        }
        .ath-card-name-row {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .ath-card-name {
          font-weight: 600;
          font-size: 0.9rem;
        }
        .ath-status-dot {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          flex-shrink: 0;
        }
        .ath-dot-connected {
          background: #22c55e;
          box-shadow: 0 0 6px rgba(34,197,94,0.4);
        }
        .ath-dot-disconnected {
          background: #52525b;
        }
        .ath-card-desc {
          display: block;
          font-size: 0.78rem;
          color: var(--text-muted, #a1a1aa);
          line-height: 1.4;
          margin-top: 2px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .ath-card-meta {
          flex-shrink: 0;
        }
        .ath-model-badge {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 0.68rem;
          padding: 3px 8px;
          border-radius: 6px;
          background: rgba(139,92,246,0.12);
          color: #a78bfa;
          white-space: nowrap;
        }

        /* Card detail */
        .ath-card-detail {
          padding: 0 14px 14px;
          display: flex;
          flex-direction: column;
          gap: 14px;
          border-top: 1px solid var(--border, #27272a);
          padding-top: 14px;
        }
        .ath-detail-row {
          display: flex;
          gap: 10px;
          align-items: flex-start;
        }
        .ath-detail-row > svg {
          color: var(--accent, #3b82f6);
          flex-shrink: 0;
          margin-top: 2px;
        }
        .ath-detail-full {
          flex: 1;
          min-width: 0;
        }
        .ath-detail-label {
          display: block;
          font-size: 0.75rem;
          font-weight: 600;
          color: var(--text-muted, #a1a1aa);
          text-transform: uppercase;
          letter-spacing: 0.04em;
          margin-bottom: 4px;
        }
        .ath-detail-value {
          display: block;
          font-size: 0.84rem;
          color: var(--text-primary, #e4e4e7);
          line-height: 1.5;
        }

        /* Prompt block */
        .ath-prompt-block {
          position: relative;
          background: #0c0c0e;
          border: 1px solid var(--border, #27272a);
          border-radius: 8px;
          padding: 12px;
          padding-top: 10px;
        }
        .ath-prompt-pre {
          margin: 0;
          font-family: "SF Mono", "Fira Code", "Cascadia Code", monospace;
          font-size: 0.78rem;
          color: #d4d4d8;
          white-space: pre-wrap;
          word-break: break-word;
          line-height: 1.55;
        }
        .ath-copy-btn {
          display: flex;
          align-items: center;
          gap: 5px;
          margin-top: 10px;
          padding: 5px 12px;
          border-radius: 6px;
          border: 1px solid var(--border, #27272a);
          background: var(--bg-secondary, #18181b);
          color: var(--text-muted, #a1a1aa);
          font-size: 0.75rem;
          cursor: pointer;
          transition: all 0.15s;
        }
        .ath-copy-btn:hover {
          background: var(--bg-hover, #1f1f23);
          color: var(--text-primary, #e4e4e7);
          border-color: var(--accent, #3b82f6);
        }

        /* Actions / configure */
        .ath-detail-actions {
          padding-top: 4px;
        }
        .ath-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 7px 14px;
          border-radius: 8px;
          border: 1px solid var(--border, #27272a);
          background: var(--bg-secondary, #18181b);
          color: var(--text-primary, #e4e4e7);
          font-size: 0.82rem;
          cursor: pointer;
          transition: all 0.15s;
        }
        .ath-btn:hover {
          background: var(--bg-hover, #1f1f23);
        }
        .ath-btn-primary {
          background: var(--accent, #3b82f6);
          border-color: var(--accent, #3b82f6);
          color: #fff;
        }
        .ath-btn-primary:hover {
          background: #2563eb;
        }
        .ath-btn-outline {
          background: transparent;
          border-color: var(--border, #3f3f46);
        }
        .ath-btn-outline:hover {
          border-color: var(--accent, #3b82f6);
          color: var(--accent, #3b82f6);
        }

        /* Config form */
        .ath-config-form {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .ath-config-form > svg {
          color: var(--text-muted, #a1a1aa);
          flex-shrink: 0;
        }
        .ath-config-input {
          flex: 1;
          padding: 7px 12px;
          border-radius: 8px;
          border: 1px solid var(--border, #27272a);
          background: var(--bg-primary, #09090b);
          color: var(--text-primary, #e4e4e7);
          font-size: 0.82rem;
          font-family: "SF Mono", monospace;
          outline: none;
        }
        .ath-config-input:focus {
          border-color: var(--accent, #3b82f6);
        }

        /* Empty state */
        .ath-empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 12px;
          padding: 48px 0;
          color: var(--text-muted, #52525b);
        }
        .ath-empty p {
          font-size: 0.92rem;
        }

        /* Footer */
        .ath-footer {
          text-align: center;
          padding: 32px 0 0;
          color: var(--text-muted, #52525b);
          font-size: 0.82rem;
        }

        /* ---- Context Assembly Panel ---- */
        .ath-context-panel {
          background: var(--bg-secondary, #18181b);
          border: 1px solid var(--border, #27272a);
          border-radius: 12px;
          margin-bottom: 20px;
          overflow: hidden;
        }
        .ath-context-header {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px 16px;
          border-bottom: 1px solid var(--border, #27272a);
          font-size: 13px;
          font-weight: 600;
          color: #8b5cf6;
        }
        .ath-context-close {
          margin-left: auto;
          background: none;
          border: none;
          color: var(--text-muted);
          cursor: pointer;
          padding: 4px;
          border-radius: 4px;
        }
        .ath-context-close:hover { background: var(--bg-tertiary, #27272a); }
        .ath-context-step {
          padding: 14px 16px;
          border-bottom: 1px solid var(--border, #27272a);
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .ath-context-step:last-child { border-bottom: none; }
        .ath-context-step label {
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          color: var(--text-muted, #71717a);
        }
        .ath-context-input {
          flex: 1;
          padding: 8px 12px;
          border: 1px solid var(--border, #27272a);
          border-radius: 6px;
          background: var(--bg-primary, #09090b);
          color: var(--text-primary, #e4e4e7);
          font-size: 13px;
          outline: none;
        }
        .ath-context-input:focus { border-color: #8b5cf6; }
        .ath-context-search-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 8px 14px;
          border: 1px solid var(--border, #27272a);
          border-radius: 6px;
          background: rgba(139, 92, 246, 0.08);
          color: #8b5cf6;
          font-size: 12px;
          font-weight: 500;
          cursor: pointer;
          flex-shrink: 0;
          transition: all 0.15s;
        }
        .ath-context-search-btn:hover { background: rgba(139, 92, 246, 0.15); }
        .ath-context-search-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .ath-spin { animation: ath-spin-anim 1s linear infinite; }
        @keyframes ath-spin-anim { to { transform: rotate(360deg); } }
        .ath-context-results {
          display: flex;
          flex-direction: column;
          gap: 4px;
          max-height: 240px;
          overflow-y: auto;
        }
        .ath-context-result {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          padding: 8px 12px;
          border-radius: 6px;
          border: 1px solid var(--border, #27272a);
          cursor: pointer;
          transition: all 0.12s;
          font-size: 13px;
        }
        .ath-context-result:hover { background: var(--bg-tertiary, #0f0f12); }
        .ath-context-result.selected {
          border-color: #8b5cf6;
          background: rgba(139, 92, 246, 0.05);
        }
        .ath-context-result input[type="checkbox"] {
          margin-top: 3px;
          accent-color: #8b5cf6;
        }
        .ath-context-result-info {
          flex: 1;
          min-width: 0;
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        .ath-context-result-title {
          font-weight: 600;
          color: var(--text-primary, #e4e4e7);
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .ath-context-result-snippet {
          font-size: 11px;
          color: var(--text-muted, #71717a);
          line-height: 1.4;
        }
        .ath-context-result-score {
          font-size: 10px;
          font-weight: 600;
          color: #8b5cf6;
          white-space: nowrap;
        }
        .ath-context-prompt {
          width: 100%;
          min-height: 120px;
          padding: 10px 12px;
          border: 1px solid var(--border, #27272a);
          border-radius: 6px;
          background: var(--bg-primary, #09090b);
          color: var(--text-primary, #e4e4e7);
          font-size: 12px;
          font-family: "SF Mono", "Fira Code", monospace;
          line-height: 1.5;
          resize: vertical;
          outline: none;
        }
        .ath-context-prompt:focus { border-color: #8b5cf6; }
      `}</style>
    </div>
  );
}

export default AIToolsHub;
