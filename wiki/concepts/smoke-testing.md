---
id: smoke-testing
title: "Smoke Testing"
type: concept
tags: ["smoke-testing", "continuous-integration", "software-testing", "ci-pipeline"]
confidence: medium
created: 2026-04-23
updated: 2026-04-23
sources: ["ing_20260423_2103298b"]
---

## Overview
Smoke testing is a preliminary testing approach used in Continuous Integration (CI) pipelines to verify that basic functionality works before running more comprehensive tests.

## Purpose
- **Preliminary verification of builds** – quickly confirm that the core components are operational.
- **Early detection of major issues** – catch severe defects before they propagate to later testing stages.

## CI Integration
- **CI commonly employs smoke testing** – automated pipelines run a lightweight set of tests immediately after a successful build.
- Provides fast feedback to developers, ensuring that only stable artifacts proceed to deeper testing suites.

## Best Practices
- Keep smoke tests concise and focused on critical paths.
- Automate execution in the pipeline to ensure consistency.
- Monitor results and iterate as the system evolves.
