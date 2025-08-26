// mockdata.ts (moved from repo root)
// Simple mock streams + items for the Streams UI.
// Each stream mirrors a mission you described and only uses links you shared.

export type Link = { label: string; url: string };
export type Item = {
  title: string;
  summary: string; // short, human-readable line about why the link matters
  links: Link[];   // one or more canonical links for the item
};

export type Stream = {
  id: string;
  name: string;        // stream name
  description: string; // user-provided mission/intent
  items: Item[];
};

export const streams: Stream[] = [
  {
    id: "ai-tools-memory",
    name: "AI Tools with Persistent User Memory & Context",
    description:
      "Find out what are the latest new products, tools, frameworks in the AI space that use LLM and develop user context, user memory, etc. For example, what kind of products connect with users' data across different platforms, integrate with the various tools they use and maximize productivity gains. And then hold memory of user, what their themes, goals and preferences are, and how do they go about doing them. With the goal of agents doing the work for users.",
    items: [
      {
        title: "Exosphere — open-source agent runtime with persistent state/memory",
        summary:
          "Agent infra with cross-session memory, node-based orchestration, and production ops.",
        links: [
          { label: "Reddit", url: "https://www.reddit.com/r/MachineLearning/comments/1n0eyrb/p_exosphere_an_open_source_runtime_for_dynamic/" },
          { label: "GitHub", url: "https://github.com/exospherehost/exospherehost" },
          { label: "Docs", url: "https://docs.exosphere.host/" }
        ]
      },
      {
        title: "ByteRover — memory layer for coding agents",
        summary:
          "Cross-session project memory, multi-assistant support, automated memory creation and retrieval.",
        links: [
          { label: "Website", url: "https://www.byterover.dev/" },
          { label: "Product Hunt", url: "https://www.producthunt.com/products/byterover" },
          { label: "Docs", url: "https://docs.byterover.dev/" },
          { label: "Hacker News", url: "https://news.ycombinator.com/item?id=45022486" }
        ]
      },
      {
        title: "Hermes 4 — hybrid reasoning models with persistent chains",
        summary:
          "Multi-step reasoning + agentic tool use; designed for complex workflows.",
        links: [
          { label: "ArXiv (tech report)", url: "https://arxiv.org/pdf/2508.18255v1" },
          { label: "HF collection", url: "https://huggingface.co/collections/NousResearch/hermes-4-collection-68a731bfd452e20816725728" }
        ]
      },
      {
        title: "TACs — type-compliant adaptation cascades",
        summary:
          "Typed probabilistic programs for LLM workflow adaptation; manages persistent context.",
        links: [{ label: "ArXiv", url: "https://arxiv.org/pdf/2508.18244v1" }]
      },
      {
        title: "RAG-Guard — zero-trust document AI (local, encrypted)",
        summary:
          "Local browser processing, encrypted storage, granular user control for document AI.",
        links: [
          { label: "GitHub", url: "https://github.com/mrorigo/rag-guard" },
          { label: "Hacker News", url: "https://news.ycombinator.com/item?id=45019397" }
        ]
      },
      {
        title: "Deep Research Agents — memory-based research automation",
        summary:
          "Multi-agent research with persistent context and parallel document analysis.",
        links: [{ label: "Blog", url: "https://www.vishnudut.com/blog/deep-research-agent" }]
      },
      {
        title: "Spring AI Framework — persistence, vectors, agents",
        summary:
          "Java-based framework for building AI apps with conversation memory and observability.",
        links: [{ label: "InfoQ", url: "https://www.infoq.com/presentations/spring-ai-framework/" }]
      },
      {
        title: "IBM MCP Gateway — protocol gateway for agents/tools/prompts",
        summary:
          "Persistent registry, cross-session context, multi-protocol support, observability.",
        links: [
          { label: "GitHub", url: "https://github.com/IBM/mcp-context-forge" },
          { label: "Docs", url: "https://ibm.github.io/mcp-context-forge/" }
        ]
      },
      {
        title: "FlashTutor — AI that turns docs into interactive study",
        summary:
          "Tracks patterns and maintains cross-session memory for personalized study paths.",
        links: [
          { label: "Website", url: "https://flashtutor.app" },
          { label: "Hacker News", url: "https://news.ycombinator.com/item?id=45018941" }
        ]
      },
      {
        title: "Whisker — real-time debugger for voice agents",
        summary:
          "Visualize agent pipelines and memory in real time for Pipecat; open source.",
        links: [
          { label: "GitHub", url: "https://github.com/pipecat-ai/whisker" },
          { label: "Hacker News", url: "https://news.ycombinator.com/item?id=45017314" }
        ]
      },
      {
        title: "GEPA — genetic-Pareto prompt evolution with memory",
        summary:
          "Language-native memory + reflective optimization; integrates retrieval infra.",
        links: [
          { label: "Reddit", url: "https://www.reddit.com/r/MachineLearning/comments/1mzxtzb/dgepa_reflective_prompt_evolution_beats_rl_with/" }
        ]
      },
      {
        title: "Chimera — enterprise agents with persistent memory/context",
        summary:
          "Role-based access, audit, cross-platform data integration; large multi-industry dataset.",
        links: [
          { label: "Help Net Security", url: "https://www.helpnetsecurity.com/2025/08/25/ai-insider-threat-simulation/" },
          { label: "ArXiv", url: "https://arxiv.org/pdf/2508.07745" }
        ]
      }
    ]
  },

  {
    id: "local-models",
    name: "Local Model Training & Indie Hardware",
    description:
      "I want to learn about finetuning and running local models on consumer hardware, or training them on indie setups, new hardware, or GPU providers, the right companies working on this, open source ecosystem and groups and forums where this is discussed.",
    items: [
      {
        title: "InternVL3.5 — praised open-source VLM series",
        summary:
          "Unified multimodal training; strong performance/parameter; good for local deployment.",
        links: [
          { label: "Reddit", url: "https://www.reddit.com/r/LocalLLaMA/comments/1mzn0zm/internvl3_5_series_is_out/" },
          { label: "Hugging Face activity", url: "https://huggingface.co/organizations/internlm/activity/all" }
        ]
      },
      {
        title: "Intel Granite Rapids — price cuts for memory-heavy builds",
        summary: "CPU platform with high memory bandwidth; helpful for large MoE/long context.",
        links: [{ label: "Reddit", url: "https://www.reddit.com/r/LocalLLaMA/comments/1mzfh73/intel_granite_rapids_cpu_on_sale_at_newegg_up_to/" }]
      },
      {
        title: "GTPO fixes GRPO artifact",
        summary:
          "Addresses shared-token penalty issue in GRPO; shows improved performance.",
        links: [{ label: "Reddit", url: "https://www.reddit.com/r/LocalLLaMA/comments/1mzquqi/grpo_please_stop_punishing_your_correct_token/" }]
      },
      {
        title: "Agent-C — tiny C-based agent",
        summary: "Extreme minimalism; relies on external APIs; example for constrained setups.",
        links: [
          { label: "Hacker News", url: "https://news.ycombinator.com/item?id=45012430" },
          { label: "GitHub", url: "https://github.com/bravenewxyz/agent-c" }
        ]
      },
      {
        title: "llama.ui — minimal privacy-focused local chat UI",
        summary: "Lightweight interface for local models.",
        links: [{ label: "Reddit", url: "https://www.reddit.com/r/LocalLLaMA/comments/1mzrb4l/llamaui_minimal_privacy_focused_chat_interface/" }]
      },
      {
        title: "DeepSeek V3.1 anomaly",
        summary: "Token generation issue highlights need for better local testing.",
        links: [{ label: "Reddit", url: "https://www.reddit.com/r/LocalLLaMA/comments/1mzsg6v/deepseek_v31_getting_token_extreme_%E6%9E%81_%E6%9E%81_out_of/" }]
      },
      {
        title: "GLM-4.5 appreciation (web dev tasks)",
        summary: "Community endorsement for Chinese OSS models in practical work.",
        links: [{ label: "Reddit", url: "https://www.reddit.com/r/LocalLLaMA/comments/1mzu2e6/glm45_appreciation_post/" }]
      },
      {
        title: "Quantization recovery (Ellora): INT4 → near-FP16",
        summary: "Self-distillation adapter recovers accuracy; less memory, faster inference.",
        links: [
          { label: "Colab", url: "https://colab.research.google.com/github/codelion/ellora/blob/main/Ellora_Recipe_1_Self_Distillation_For_Quantization_Recovery.ipynb" },
          { label: "HF adapter", url: "https://huggingface.co/codelion/Qwen3-0.6B-accuracy-recovery-lora" },
          { label: "GitHub", url: "https://github.com/codelion/ellora" }
        ]
      },
      {
        title: "Qwen3 on Android (Termux + llama.cpp)",
        summary: "Mobile local inference; 6–25 tok/s on Snapdragon 8 Gen1 reported.",
        links: [{ label: "Reddit", url: "https://www.reddit.com/r/LocalLLaMA/comments/1myxhda/is_this_local_enough_qwen3_4b_q4k_m_on_llamacpp/" }]
      },
      {
        title: "Manga translation tool (OCR + image processing)",
        summary: "Open-source prototype running on HF Spaces.",
        links: [
          { label: "HF Space", url: "https://huggingface.co/spaces/Curify/manga_translation" },
          { label: "Reddit", url: "https://www.reddit.com/r/LocalLLaMA/comments/1myvpqv/open_source_tool_for_manga_translation/" }
        ]
      },
      {
        title: "Unsloth — memory-efficient finetuning updates",
        summary: "Improvements for resource-constrained training; RTX 50 support, long-context tricks.",
        links: [{ label: "Website", url: "https://unsloth.ai/" }]
      },
      {
        title: "RTX PRO 6000 MAX-Q (Blackwell) for LLM",
        summary: "Workstation-grade GPU; major training/inference speedups.",
        links: [{ label: "Reddit", url: "https://www.reddit.com/r/LocalLLaMA/comments/1my3why/rtx_pro_6000_maxq_blackwell_for_llm/" }]
      },
      {
        title: "ArchiFactory + PromptServer",
        summary: "Training scripts and benchmark helpers for local/indie workflows.",
        links: [
          { label: "ArchiFactory (GitHub)", url: "https://github.com/gabrielolympie/ArchiFactory" },
          { label: "PromptServer (GitHub)", url: "https://github.com/gabrielolympie/PromptServer" }
        ]
      },
      {
        title: "LLM-Ripper — modular model deconstruction",
        summary: "Extract, analyze, and transplant transformer components.",
        links: [
          { label: "Reddit", url: "https://www.reddit.com/r/LocalLLaMA/comments/1my3odz/just_ripped_a_llm_apart_and_it_still_works/" },
          { label: "GitHub", url: "https://github.com/qrv0/LLM-Ripper" }
        ]
      },
      {
        title: "GPU utilization & budget hardware threads",
        summary: "Community discussions on dual-GPU tuning and affordable V100s.",
        links: [
          { label: "Utilization", url: "https://www.reddit.com/r/LocalLLaMA/comments/1my4exj/how_does_gpu_utilization_works/" },
          { label: "V100 deal", url: "https://www.reddit.com/r/LocalLLaMA/comments/1my3wl1/just_snagged_a_tesla_v100_16gb_for_200_pcie_not/" }
        ]
      },
      {
        title: "llama.cpp update + Mamba comparisons",
        summary: "Commit adds support for new family; community compares hybrid architectures.",
        links: [
          { label: "llama.cpp commit", url: "https://github.com/ggml-org/llama.cpp/commit/b1afcab804e3281867a5471fbd701e32eb32e512" },
          { label: "Reddit (Mamba time)", url: "https://www.reddit.com/r/LocalLLaMA/comments/1my39ja/its_mamba_time_comparing_nemotron_nano_v2_vs/" }
        ]
      },
      {
        title: "DeepSeek-V3.1-Base (685B MoE)",
        summary: "Massive open model release; practical only for org-scale hardware.",
        links: [
          { label: "Reddit", url: "https://www.reddit.com/r/LocalLLaMA/comments/1mukl2a/deepseekaideepseekv31base_hugging_face/" },
          { label: "Hugging Face", url: "https://huggingface.co/deepseek-ai/DeepSeek-V3.1-Base" }
        ]
      },
      {
        title: "Claude Context (MCP tool) — code retrieval",
        summary: "Open-source retrieval for Claude Code; reduces token usage.",
        links: [
          { label: "GitHub", url: "https://github.com/zilliztech/claude-context" },
          { label: "Article", url: "https://zc277584121.github.io/ai-coding/2025/08/15/build-code-retrieval-for-cc.html" }
        ]
      },
      {
        title: "Power & platform threads (dual GPUs, PSU sizing, training providers)",
        summary: "Practical advice on PSU sizing, board choices, and cloud providers.",
        links: [
          { label: "PSU sizing", url: "https://www.reddit.com/r/LocalLLaMA/comments/1muknd5/which_psu_for_a_dual_rtx_pro_6000_build/" },
          { label: "5090+4090 setup", url: "https://www.reddit.com/r/LocalLLaMA/comments/1muh048/need_help_with_5090_4090_dual_gpu_setup/" },
          { label: "CoreWeave Q&A", url: "https://www.reddit.com/r/LocalLLaMA/comments/1mujjtp/looking_for_an_online_service_for_training/" }
        ]
      },
      {
        title: "Ecosystem pulse",
        summary: "Kimi K2 agents, Qwen 3 Coder benchmarks, FlashAttention 4 leak, LFM2-VL in llama.cpp, Memori engine; general forum.",
        links: [
          { label: "Kimi K2", url: "https://www.reddit.com/r/LocalLLaMA/comments/1mtk03a/kimi_k2_is_really_really_good/" },
          { label: "Qwen 3 Coder", url: "https://www.reddit.com/r/LocalLLaMA/comments/1mto8fa/new_code_benchmark_puts_qwen_3_coder_at_the_top/" },
          { label: "FlashAttention 4 leak", url: "https://www.reddit.com/r/LocalLLaMA/comments/1mt9htu/flashattention_4_leak/" },
          { label: "LFM2-VL support", url: "https://www.reddit.com/r/LocalLLaMA/comments/1mthwu7/lfm2vl_family_support_is_now_available_in_llamacpp/" },
          { label: "Memori engine", url: "https://www.reddit.com/r/LocalLLaMA/comments/1mto88l/we_opensourced_memori_a_memory_engine_for_ai/" },
          { label: "NVIDIA blog (RTX 5090)", url: "https://blogs.nvidia.com/blog/rtx-ai-garage-openai-oss/" },
          { label: "LocalLLaMA forum", url: "https://www.reddit.com/r/LocalLLaMA/" }
        ]
      }
    ]
  },

  {
    id: "agent-protocols",
    name: "Agent Frameworks, Protocols & Debugging",
    description:
      "Frameworks, protocols and tooling for agent orchestration, memory, and debugging—voice pipelines, registries, typed workflows.",
    items: [
      {
        title: "IBM MCP Gateway — protocol hub for agents/tools/prompts",
        summary: "Central registry, cross-session context, observability.",
        links: [
          { label: "GitHub", url: "https://github.com/IBM/mcp-context-forge" },
          { label: "Docs", url: "https://ibm.github.io/mcp-context-forge/" }
        ]
      },
      {
        title: "Whisker — live debugger for voice agents (Pipecat)",
        summary: "Graphical inspector for pipelines and memory state.",
        links: [
          { label: "GitHub", url: "https://github.com/pipecat-ai/whisker" },
          { label: "Hacker News", url: "https://news.ycombinator.com/item?id=45017314" }
        ]
      },
      {
        title: "Exosphere — agent runtime with persistence",
        summary: "Scalable agents, persistent memory, Kubernetes-native.",
        links: [
          { label: "GitHub", url: "https://github.com/exospherehost/exospherehost" },
          { label: "Docs", url: "https://docs.exosphere.host/" }
        ]
      },
      {
        title: "TACs & GEPA — structured adaptation + reflective memory",
        summary: "Typed cascades (TACs) and memory-based prompt evolution (GEPA).",
        links: [
          { label: "TACs (ArXiv)", url: "https://arxiv.org/pdf/2508.18244v1" },
          { label: "GEPA (Reddit)", url: "https://www.reddit.com/r/MachineLearning/comments/1mzxtzb/dgepa_reflective_prompt_evolution_beats_rl_with/" }
        ]
      },
      {
        title: "Spring AI — agents with memory & observability",
        summary: "Production posture for Java ecosystems.",
        links: [{ label: "InfoQ", url: "https://www.infoq.com/presentations/spring-ai-framework/" }]
      }
    ]
  },

  {
    id: "ai-security-enterprise",
    name: "AI Security & Enterprise Agents",
    description:
      "Security-forward and enterprise-grade agent systems: zero-trust document AI, auditability, role-based access, cross-platform ops.",
    items: [
      {
        title: "RAG-Guard — local, encrypted, zero-trust document AI",
        summary: "Granular control; runs in browser; multi-LLM integration.",
        links: [
          { label: "GitHub", url: "https://github.com/mrorigo/rag-guard" },
          { label: "Hacker News", url: "https://news.ycombinator.com/item?id=45019397" }
        ]
      },
      {
        title: "Chimera — enterprise agents with audit & RBAC",
        summary: "Autonomous multi-agent workflows with persistent memory and logs.",
        links: [
          { label: "Help Net Security", url: "https://www.helpnetsecurity.com/2025/08/25/ai-insider-threat-simulation/" },
          { label: "ArXiv", url: "https://arxiv.org/pdf/2508.07745" }
        ]
      }
    ]
  }
];
