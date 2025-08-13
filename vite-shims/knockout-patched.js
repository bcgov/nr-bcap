// IMPORTANT: import the real Knockout from a non-aliased id
import ko from 'knockout-original';

// Guard double registration of components (idempotent)
if (ko?.components && !ko.components.__wrappedRegister) {
  const orig = ko.components.register.bind(ko.components);
  ko.components.register = (name, config) => {
    if (ko.components.isRegistered?.(name)) return;
    return orig(name, config);
  };
  ko.components.__wrappedRegister = true;
}

export default ko;
// keep named exports working
export * from 'knockout-original';