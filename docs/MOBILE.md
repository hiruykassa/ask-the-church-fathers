# React Native port notes

The web app is structured so screens and logic can move to React Native with minimal rewrites.

## Reuse as-is

- `src/theme/tokens.js` — map to `StyleSheet` / theme context (`themes.light`, `themes.dark`)
- `src/theme/ThemeProvider.jsx` — replace with RN context + `AsyncStorage` for `atcf-color-mode`
- `src/api/client.js` — change `API_BASE` for device (e.g. `http://10.0.2.2:5001` on Android emulator)
- `src/utils/authorQuery.js` — pure JS
- `src/constants/*` — data only

## Replace on mobile

| Web | React Native |
|-----|----------------|
| `react-router-dom` | `@react-navigation/native` (stack + bottom tabs) |
| `src/components/layout/MobileTabBar.jsx` | `@react-navigation/bottom-tabs` |
| `src/styles/*.css` | `StyleSheet.create` from `tokens.js` |
| `src/hooks/useScrollTop.js` | `ScrollView` ref + `onScroll` |
| `src/hooks/useScrollReveal.js` | `Animated` or skip |
| `react-icons` | `@expo/vector-icons` or similar |
| `react-markdown` | `react-native-markdown-display` |

## Suggested screen map

- **HomeScreen** — current `App.jsx` (search + library)
- **ReadScreen** — current `ReadPage.jsx`
- **SavedScreen** — tab from `SavedView`

## Env

Set `VITE_API_URL` for production web builds. For RN, use `expo-constants` or `.env` with the same base URL pattern.
