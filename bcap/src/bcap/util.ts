export const getDisplayValue = (value: object) => {
    return value?.node_value ? value.display_value : "";
};

export const isEmpty = (value: object) => {
    return !value?.node_value;
};
