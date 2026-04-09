# Tailwind Config Requirements for Funnel Modals

The funnel modal components use the following Tailwind features. Ensure these are configured in your `tailwind.config.ts`:

## Custom Colors

The components use `lena-*` color variables (lena-50 through lena-950). These should already be configured in your Tailwind theme.

Example configuration:
```typescript
theme: {
  colors: {
    // ... other colors
    'lena': {
      '50': '#f8f9ff',
      '100': '#f0f2ff',
      '200': '#e6ebff',
      '300': '#d4dfff',
      '400': '#b8c8ff',
      '500': '#8b9eff',
      '600': '#6b7fff',
      '700': '#5360ff',
      '800': '#3d4bff',
      '900': '#2a3aff',
      '950': '#1f2aaa',
    },
  },
}
```

## Custom Animations

The ModalOverlay component uses `animate-fadeIn`. Add this to your Tailwind config:

```typescript
theme: {
  extend: {
    animation: {
      fadeIn: 'fadeIn 0.3s ease-in-out',
    },
    keyframes: {
      fadeIn: {
        '0%': { opacity: '0', transform: 'scale(0.95)' },
        '100%': { opacity: '1', transform: 'scale(1)' },
      },
    },
  },
}
```

## Font Configuration

The components use Inter font (inherited globally). Ensure this is configured:

```typescript
theme: {
  fontFamily: {
    sans: ['Inter', 'system-ui', 'sans-serif'],
  },
}
```

## Complete Example

If your `tailwind.config.ts` is missing these, here's what to add:

```typescript
import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'lena': {
          '50': '#f8f9ff',
          '100': '#f0f2ff',
          '200': '#e6ebff',
          '300': '#d4dfff',
          '400': '#b8c8ff',
          '500': '#8b9eff',
          '600': '#6b7fff',
          '700': '#5360ff',
          '800': '#3d4bff',
          '900': '#2a3aff',
          '950': '#1f2aaa',
        },
      },
      animation: {
        fadeIn: 'fadeIn 0.3s ease-in-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
    },
  },
  plugins: [],
};

export default config;
```

## Verification

Before using the funnel components, verify that:

1. `lena-*` colors are accessible in your project
2. `animate-fadeIn` can be used in Tailwind classes
3. Inter font is loaded globally
4. All className utilities can be properly compiled

If you get undefined color or animation errors, add the configuration snippets above to your `tailwind.config.ts`.
