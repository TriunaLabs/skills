# Technical and structured-data guidance

Apply current, primary-source guidance when implementation details may have changed.

## Baseline

- Give the page a descriptive `<title>`, one clear primary heading, a canonical URL when known, and a useful meta description.
- Keep essential claims and decision information in textual form and available without requiring a click, animation, canvas, or client-only rendering.
- Use semantic landmarks and a logical heading structure for people using assistive technology.
- Write alt text for the image's purpose in context. Use `alt=""` for decoration.
- Ensure crawl controls match the publishing intent. Do not remove `noindex` or change crawler access without authorization.
- Test mobile layout, keyboard focus, performance, links, and rendered/source parity.

Google states that ordinary SEO fundamentals remain the basis for its generative search features and that there is no special AI schema or required AI text file. It also says structured data must match visible content and does not guarantee display. Verify current guidance before making time-sensitive claims:

- Google generative AI search guidance: https://developers.google.com/search/docs/fundamentals/ai-optimization-guide
- Google AI features and websites: https://developers.google.com/search/docs/appearance/ai-features
- Structured data policies: https://developers.google.com/search/docs/appearance/structured-data/sd-policies
- OpenAI crawler controls: https://developers.openai.com/api/docs/bots
- Schema vocabulary: https://schema.org/

## Type selection

Use the narrowest type that accurately describes the page's main visible entity, commonly `Organization`, `Person`, `Product`, `SoftwareApplication`, `Service`, `Article`, or `BreadcrumbList`. Include properties only when their values are visible or otherwise allowed by the applicable policy and are current.

Validate JSON syntax locally. For Google-specific eligibility, use the Rich Results Test and URL Inspection where appropriate. Schema.org validity and Google feature eligibility are separate questions.

Do not add `FAQPage` merely because a page has FAQs. Google retired FAQ rich results in May 2026, and FAQ markup is not evidence that an AI system will cite a page.

## Crawler controls

Treat Googlebot, Google-Extended, OAI-SearchBot, GPTBot, and ChatGPT-User as distinct controls with different purposes. Read current provider documentation before editing `robots.txt`. Report the existing policy and proposed effect before changing it.
