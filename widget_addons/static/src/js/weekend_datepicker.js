/** @odoo-module **/

import { registry } from "@web/core/registry";
import { DateField, dateField } from "@web/views/fields/date/date_field";
import { DateTimePicker } from "@web/core/datetime/datetime_picker";

class WeekendDateTimePicker extends DateTimePicker {
    /**
     * Override to inject daysOfWeekDisabled into every props update.
     * In Odoo 17, the picker receives props directly — there is no
     * extractProps / pickerOptions pattern like v16.
     */
    get minDate() { return super.minDate; }
    get maxDate() { return super.maxDate; }

    isDateValid(date) {
        // Block Saturday (6) and Sunday (0) from being selectable
        const day = date.weekday % 7; // luxon weekday: 1=Mon … 7=Sun → mod 7 gives 0=Sun,6=Sat
        if (day === 0 || day === 6) {
            return false;
        }
        return super.isDateValid(date);
    }

    isDayDisabled(date) {
        const day = date.weekday % 7;
        if (day === 0 || day === 6) {
            return true;
        }
        return super.isDayDisabled ? super.isDayDisabled(date) : false;
    }
}

WeekendDateTimePicker.template = DateTimePicker.template;
WeekendDateTimePicker.props    = DateTimePicker.props;

class WeekendDateField extends DateField {
    /**
     * In Odoo 17, DateField renders its picker via this.pickerComponent.
     * We swap it out for our subclassed picker.
     */
    setup() {
        super.setup();
    }

    get pickerComponent() {
        return WeekendDateTimePicker;
    }

    /**
     * Prevent manual typing of weekend dates by validating on commit.
     */
    async onDateTimeChanged(value) {
        if (value) {
            const day = value.weekday % 7; // 0 = Sunday, 6 = Saturday
            if (day === 0 || day === 6) {
                // Reject the value silently — picker already blocks clicks,
                // but typed input can still slip through
                this.state.value = this.props.value || false;
                return;
            }
        }
        return super.onDateTimeChanged(value);
    }
}

// Inherit everything from the base field
WeekendDateField.template      = DateField.template;
WeekendDateField.components    = {
    ...DateField.components,
    DateTimePicker: WeekendDateTimePicker,  // override the picker used in the template
};
WeekendDateField.props         = DateField.props;
WeekendDateField.defaultProps  = DateField.defaultProps;
WeekendDateField.supportedTypes = DateField.supportedTypes;

registry.category("fields").add("no_weekend_date", WeekendDateField);