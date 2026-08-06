> In this document, we are using the Dominican Republic as a case study, but keep in mind that the pipeline is designed to be agnostic to the country. See [README](../README.md) or [Architecture](architecture.md) for more details.

# Ojo Crítico — Case Study

**Website:** [Ojo Crítico](https://www.ojocritico.org/)

Ojo Crítico is a news website that cross-checks, verifies and publishes news articles from multiple sources in the Dominican Republic.

## Why this case

The Dominican Republic is facing a lack of trust in traditional media outlets. Many alternative sources of news are not reliable and often spread misinformation deliberately to influence public opinion.

I realized that there was not a single source where you could find or read the news without feeling like you were being manipulated or influenced.

There was no single place to read the news without feeling manipulated or influenced—and no local equivalent of [AP Fact Check](https://apnews.com/ap-fact-check) or [Reuters Fact Check](https://www.reuters.com/factcheck/). Ojo Crítico was built to fill that gap.

## Media Landscape

My criterion for selecting the sources was one simple rule: **the source must be popular and well-known in the Dominican Republic (more than 100,000 monthly visits).**

Also, I tried to keep a wide range of sources to ensure that the news is not biased toward a particular political party or ideology.

**Sources:**
- [Somos Pueblo](https://somospueblo.com/)
- [El Nuevo Diario](https://elnuevodiario.com.do/)
- [Listín Diario](https://listindiario.com/)
- [Diario Libre](https://diariolibre.com/)
- [Hoy](https://hoy.com.do/)
- [Acento](https://acento.com.do/)
- [Remolacha](https://remolacha.net/)
- [El Caribe](https://elcaribe.com.do/)
- [El Nacional](https://elnacional.com.do/)
- [El Día](https://eldia.com.do/)

## Findings & limits

- Most controversial articles are published by the same few outlets, which means clusters are often small (less than 4 articles) and harder to treat as reliable.

- The "opinion" articles are not fact-checked or verified by the source, which is where the real risk of being manipulated or influenced resides.

- There are no good indicators that the project can be sustained in the long term by donations, and we might need to consider ads or any other monetization strategy. This might threaten the independence of the project, which is super crucial.

## End-to-End Example

> [TBD]


## Final thoughts

The project is a work in progress and there are still a lot of things to improve. But that will only depend on the community's support and the project's sustainability.
