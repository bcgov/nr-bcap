import ko from 'knockout';

if (!ko.components.__wrappedRegister) {
  const orig = ko.components.register.bind(ko.components);
  ko.components.register = (name, config) => {
    if (ko.components.isRegistered(name)) return;
    return orig(name, config);
  };
  ko.components.__wrappedRegister = true;
}