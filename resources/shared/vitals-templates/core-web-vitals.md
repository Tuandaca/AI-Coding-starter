# Core Web Vitals Templates

## LCP (Largest Contentful Paint) - Target: < 2.5s

### Optimization Checklist
- [ ] Preload critical resources (fonts, hero images)
- [ ] Optimize server response times (TTFB < 600ms)
- [ ] Use CDN for static assets
- [ ] Implement critical CSS inlining
- [ ] Avoid render-blocking resources

### Measurement
```javascript
// web-vitals library
import { onLCP } from 'web-vitals';
onLCP(console.log);
```

## FID (First Input Delay) - Target: < 100ms

### Optimization Checklist
- [ ] Minimize main thread work
- [ ] Break up long tasks (> 50ms)
- [ ] Use web workers for heavy computation
- [ ] Defer non-critical JavaScript
- [ ] Optimize event handlers

### Measurement
```javascript
import { onFID } from 'web-vitals';
onFID(console.log);
```

## CLS (Cumulative Layout Shift) - Target: < 0.1

### Optimization Checklist
- [ ] Reserve space for images/ads/embeds
- [ ] Avoid inserting content above existing content
- [ ] Use transform animations instead of layout
- [ ] Font loading: `font-display: optional` or `swap`
- [ ] Reserve space for dynamic content

### Measurement
```javascript
import { onCLS } from 'web-vitals';
onCLS(console.log);
```

## INP (Interaction to Next Paint) - Target: < 200ms

### Optimization Checklist
- [ ] Reduce JavaScript execution time
- [ ] Optimize event callbacks
- [ ] Use `isInputPending()` for yielding
- [ ] Virtualize long lists
- [ ] Debounce/throttle expensive operations
