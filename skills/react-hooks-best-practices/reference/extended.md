# react-hooks-best-practices Extended Reference

This file preserves detailed material moved out of `SKILL.md` for progressive disclosure. Load it only when the current task needs the specific examples, commands, templates, or checklists below.

Moved content starts at: `## Custom Hooks`.

## Custom Hooks

### Hooks Share Logic, Not State

```tsx
// Each call gets independent state
function StatusBar() {
  const isOnline = useOnlineStatus(); // Own state
}

function SaveButton() {
  const isOnline = useOnlineStatus(); // Separate state instance
}
```

### Name Hooks useXxx Only If They Use Hooks

```tsx
// BAD: useXxx but doesn't use hooks
function useSorted(items) {
  return items.slice().sort();
}

// GOOD: Regular function
function getSorted(items) {
  return items.slice().sort();
}

// GOOD: Uses hooks, so prefix with use
function useAuth() {
  return useContext(AuthContext);
}
```

### Avoid "Lifecycle" Hooks

```tsx
// BAD: Custom lifecycle hooks
function useMount(fn) {
  useEffect(() => {
    fn();
  }, []); // Missing dependency, linter can't catch it
}

// GOOD: Use useEffect directly
useEffect(() => {
  doSomething();
}, [doSomething]);
```

### Keep Custom Hooks Focused

```tsx
// GOOD: Focused, concrete use cases
useChatRoom({ serverUrl, roomId });
useOnlineStatus();
useFormInput(initialValue);

// BAD: Generic, abstract hooks
useMount(fn);
useEffectOnce(fn);
useUpdateEffect(fn);
```

## Component Patterns

### Controlled vs Uncontrolled

```tsx
// Uncontrolled: component owns state
function SearchInput() {
  const [query, setQuery] = useState('');
  return <input value={query} onChange={e => setQuery(e.target.value)} />;
}

// Controlled: parent owns state
function SearchInput({ query, onQueryChange }) {
  return <input value={query} onChange={e => onQueryChange(e.target.value)} />;
}
```

### Prefer Composition Over Prop Drilling

```tsx
// BAD: Prop drilling
<App user={user}>
  <Layout user={user}>
    <Header user={user}>
      <Avatar user={user} />
    </Header>
  </Layout>
</App>

// GOOD: Composition with children
<App>
  <Layout>
    <Header avatar={<Avatar user={user} />} />
  </Layout>
</App>

// GOOD: Context for truly global state
<UserContext.Provider value={user}>
  <App />
</UserContext.Provider>
```

### flushSync for Synchronous DOM Updates

```tsx
// When you need to read DOM immediately after state update
import { flushSync } from 'react-dom';

function handleAdd() {
  flushSync(() => {
    setTodos([...todos, newTodo]);
  });
  // DOM is now updated, safe to read
  listRef.current.lastChild.scrollIntoView();
}
```

## Summary: Decision Tree

1. **Need to respond to user interaction?** Use event handler
2. **Need computed value from props/state?** Calculate during render
3. **Need cached expensive calculation?** Use useMemo
4. **Need to reset state on prop change?** Use key prop
5. **Need to synchronize with external system?** Use Effect with cleanup
6. **Need non-reactive code in Effect?** Use useEffectEvent
7. **Need mutable value that doesn't trigger render?** Use ref
