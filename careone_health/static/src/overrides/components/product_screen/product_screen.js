/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";

const gasStationDict = {
    "Fuel 95 -- بنزين 95": 2.33,
    "Fuel 91 -- بنزين 91": 2.18,
    "Diesel -- ديزل": 1.15,
};

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    },

    async updateSelectedOrderline({ buffer, key }) {
        await super.updateSelectedOrderline({ buffer, key });
        console.log({ buffer, key });
        const selectedLine = this.currentOrder.get_selected_orderline();
        if (selectedLine){
            console.log(selectedLine);
            console.log(`${selectedLine.product.name} PRODUCT display NAME ${selectedLine.product.display_name} \
                NUMPAD IS ${this.pos.numpadMode} \
                GAS STATION IS ${this.pos.config.is_gas_station}`)
        
            if (
                gasStationDict[selectedLine.product.display_name] &&
                this.pos.numpadMode === "price" &&
                this.pos.config.is_gas_station
            ) {
                const totalPrice = parseFloat(buffer);
                console.log(`WHAT IS NUMPAD ${totalPrice}`)
                if (!isNaN(totalPrice)) {
                    const pricePerLiter =
                        gasStationDict[selectedLine.product.display_name];
                    const quantity = totalPrice / pricePerLiter; // Calculate quantity based on the specific fuel price

                    selectedLine.set_quantity(quantity);
                    selectedLine.set_unit_price(pricePerLiter); // Set unit price based on the specific fuel
                    this.currentOrder
                        .get_selected_orderline()
                        // Not used anymore 
                        //.trigger("change", this.currentOrder);
                }
            }else {
                console.log("Ensure the product name is exact and gas station is set and numpad mode is price")
            }
        }else {
            console.log("No line selected");
        }
    } 
});
