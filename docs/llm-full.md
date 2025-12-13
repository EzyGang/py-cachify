---
hide:
  - toc
  - navigation
---
# LLM Full Documentation View

This page programmatically includes all other documentation pages.
It is intended for tools and LLMs that want a single-page view of the entire documentation
while keeping each source file as the single source of truth.

> NOTE: This page is built using the `include-markdown` plugin.
> Each section below inlines the contents of an existing documentation file using Jinja-style directives.

---

## Top-level

{% include-markdown "index.md" %}

{% include-markdown "examples.md" %}
---

## Tutorial

{% include-markdown "tutorial/index.md" %}

### Initial Setup

{% include-markdown "tutorial/initial-setup/install.md" %}

{% include-markdown "tutorial/initial-setup/initialization.md" %}

### Cached Decorator

{% include-markdown "tutorial/cached-decorator/first-steps.md" %}

{% include-markdown "tutorial/cached-decorator/dynamic-cache-keys.md" %}

{% include-markdown "tutorial/cached-decorator/specifying-ttl-and-encoder-decoder.md" %}

{% include-markdown "tutorial/cached-decorator/reset-attribute.md" %}

### Locks

{% include-markdown "tutorial/locks/locks-intro.md" %}

{% include-markdown "tutorial/locks/simple-locks.md" %}

{% include-markdown "tutorial/locks/lock-parameters.md" %}

{% include-markdown "tutorial/locks/lock-methods.md" %}

{% include-markdown "tutorial/locks/lock-as-decorator.md" %}

### Once Decorator

{% include-markdown "tutorial/once-decorator/index.md" %}

---

## API Reference

{% include-markdown "reference/init.md" %}

{% include-markdown "reference/cached.md" %}

{% include-markdown "reference/lock.md" %}

{% include-markdown "reference/once.md" %}

---

## Help & Contribution

{% include-markdown "help/help.md" %}

{% include-markdown "help/contribution.md" %}
{% include-markdown "release-notes.md" %}

{% endraw %}
