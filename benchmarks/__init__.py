"""octobench benchmark adapters.

A small, config-driven framework for running external benchmarks through the
same flow as local cases and SWE-bench-Live: task -> agent SETUP -> verdict ->
judge -> score. Each benchmark is a YAML config (configs/benchmarks/*.yaml) bound
to one of a few reusable adapter engines:

- qa            (benchmarks.qa.QAAdapter): single-turn QA. modes:
                  mcq | final_answer | constraint  -> objective verdict
                  judge_text                       -> LLM-judge verdict
- docker_task   (benchmarks.docker_task.DockerTaskAdapter): build/derive a Docker
                  image, prep the env, run the agent, run a verify command, and
                  derive a programmatic pass/fail (generalizes SWE-bench-Live).
- swebench_live (benchmarks.swebench_live.SwebenchLiveAdapter): real post-2024
                  GitHub issues, repo-in-image, FAIL_TO_PASS/PASS_TO_PASS verdict.

See configs/benchmarks/README.md for the catalog across domains and which
adapters are data-complete vs. need an upstream Docker image / dataset stood up.
"""
