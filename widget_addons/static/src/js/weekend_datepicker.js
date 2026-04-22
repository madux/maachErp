/** @odoo-module **/

import { registry } from "@web/core/registry";
import { DateField } from "@web/views/fields/date/date_field";

// Create a new field widget based on core DateField
class WeekendDateField extends DateField {
    // IMPORTANT: inject into props.pickerOptions via extractProps,
    // because the template uses props.pickerOptions (not a class getter)
    static extractProps(env) {
        // call the core static to get base props first
        const props = DateField.extractProps(env);
        const merged = { ...(props.pickerOptions || {}) };

        // 0 = Sunday, 6 = Saturday
        merged.daysOfWeekDisabled = [0, 6];

        return { ...props, pickerOptions: merged };
    }
}

// Reuse the same template & components as core DateField
WeekendDateField.template = DateField.template;
WeekendDateField.components = DateField.components;
WeekendDateField.props = DateField.props;
WeekendDateField.defaultProps = DateField.defaultProps;
WeekendDateField.supportedTypes = DateField.supportedTypes;

// Register under a new widget name
registry.category("fields").add("no_weekend_date", WeekendDateField);
