odoo.define('eha_website.covid_19booking12', function(require) {
    'use strict';

    require('web.dom_ready');
    var session = require('web.Session');
    var ajax = require('web.ajax');

    // COVID 19 BOOKINGS
    $(document).ready(function() {
        // Add preloader to submit / proceed button
        let btn = $(".btn.preloader")
        btn.click(function(ev) {
            btn.html("<i  class'fa fa-spinner fa-spin'>Loading ...</i>")
        });

        function checkDiscount(code) {
            return ajax.jsonRpc("/covid/check/discount", 'call', { 'code': code })
        }

        $('#has_promo_code').on('click', function(ev) {
            var $target = $(ev.currentTarget);
            var is_checked = $target.is(":checked");
            var name = $('input[name="name"]').val();
            if (is_checked) {
                $('input[name="is-member"]').parent().hide();
                if (!name) {
                    alert('Please Input the name of member!');
                    $target.trigger('click');
                }
                $('.promo-container').removeClass('d-none');
            } else {
                $('input[name="is-member"]').parent().show();
                $('.promo-container').addClass('d-none');
            }
        });

        // garbage collect any existing object in localStorage
        var host = window.location.origin;
        var url = window.location.href;
        var startPage = host + "/services/buy-covid19-test";
        var covid19Pcr1 = host + "/shop/product/covid-19-pcr-eha-clinics-covid19-pcr-test-for-international-travel-7662";
        var covid19Pcr2 = host + "/shop/product/covid-19-pcr2-eha-clinics-covid19-pcr-test-5886";

        // Function to format number as Commas
        var formatCurrency = function(value) {
            if (value) {
                return value.toString().replace(/\D/g, "").replace(/\B(?=(\d{3})+(?!\d))/g, ",")

            }
        }

        function addToOrder(products, productcode, antibodySelected = false) {
            var totalprice = 0
            var product = products.filter(p => p.code == productcode)
            console.log('PRoduct found IS ==>', product)
            if (product) {
                product = product[0]
                var order = {
                    "productid": product.id,
                    "productname": product.name,
                    "productprice": product.price,
                    "productcode": product.code,
                    "total": product.price,
                    "membersPrice": product.members_price,
                    "membersTotalPrice": product.members_price,
                    "hscSelected": false,
                    "thirdparty_partner_id": $("input[name='thirdparty_partner_id']").val(),
                    "isPcrSelected": true ? isCheckedPcr() : false,
                    "isAntigenSelected": true ? isCheckedAntigen() : false,
                }
                console.log('PRODUCT PRICE IS ==>', product.price)
            }

            if (antibodySelected) {
                var antibodyProduct = products.filter(p => p.code == 'ANTIBODY')
                if (antibodyProduct) {
                    antibodyProduct = antibodyProduct[0]
                    order["antibodyproductid"] = antibodyProduct.id
                    order['antibodyproductprice'] = antibodyProduct.price
                    order["antibodyproductname"] = antibodyProduct.name,
                        order["antibodySelected"] = true
                    order["total"] = (product != undefined) ? product.price + antibodyProduct.price : product.price
                    order["membersTotalPrice"] = order.membersPrice + antibodyProduct.price
                }
            }
            localStorage.setItem("order", JSON.stringify(order));
            displayPrice(order['total'], order['membersPrice']);
            order = JSON.parse(localStorage.getItem("order"));
            return order
        }

        function removeFromOrder(antibodySelected = false) {
            console.log("ANTIBODY REMOVEDs")
            if (antibodySelected) {
                let order = JSON.parse(localStorage.getItem("order"))
                order["antibodyproductid"] = null
                order['antibodyproductprice'] = 0.00
                order["antibodyproductname"] = ""
                order["antibodySelected"] = false
                localStorage.setItem("order", JSON.stringify(order))
                console.log("MY NEW ORDER " + JSON.stringify(localStorage.getItem("order")))
            } else {
                //only one product can be added to order, so when it is removed, we will destroy the order
                localStorage.setItem("order", "")
            }
        }

        function isCheckedPcr() {
            if ($('#testtype_option_id').prop("checked")) {
                return true
            }
            return false
        }

        function isCheckedAntigen() {
            if ($('#testtype_antigen_option_id').prop("checked")) {
                return true
            }
            return false
        }

        function isCheckedTravel() {
            if ($('#is_international_travel').prop("checked")) {
                return true
            }
            return false
        }

        function isCheckedAntibody() {
            if ($('#is_anti_body').prop("checked")) {
                return true
            }
            return false
        }

        /////////// FUNCTIONS END HERE

        //// DOM MANIPULATION STARTS HERES
        function calculatePrice(products, defaultcode) {
            var Product = products.filter(p => p.code == defaultcode)[0]
            var totalprice = 0
            var membersPrice = 0
            if (Product !== undefined) {
                totalprice = Product.price
                membersPrice = Product.members_price
            }
            return { 'totalprice': totalprice, 'membersPrice': membersPrice }
        }

        function displayPrice(totalprice, membersPrice) {
            //update order total
            let order = JSON.parse(localStorage.getItem("order"))
            order.total = totalprice
            localStorage.setItem("order", JSON.stringify(order))
                //display order total
            $('#product_price_id').html('₦ ' + formatCurrency(totalprice) + ' ' + '(₦ ' + formatCurrency(membersPrice) + " for <span class='text-primary'>members</span>)");
        }

        function processOrder(params) {
            var products = params['data'];
            var localStorage = window.localStorage;
            console.log('Processed products ==>', products)

            // This auto check travel check box for International travel covid19 purchase.
            if (window.location.href.indexOf("is_travel") > -1) {
                $('#is_international_travel').prop('checked', true);
                addToOrder(products, "COVID-19-PCR", false)
                var productPrices = calculatePrice(products, "COVID-19-PCR")
                displayPrice(productPrices.totalprice, productPrices.membersPrice)
            } else {
                //PCR non travel is the default, add it to cart on page load
                addToOrder(products, 'COVID-19-PCR2', false)
            }
            var temp_order = JSON.parse(localStorage.getItem("order"));
            if (params['promo_id']) {
                temp_order['code_promo_program_id'] = params['promo_id'];
                localStorage.setItem("order", JSON.stringify(temp_order));
            }

            var order = {
                'antibodyproductid': false,
                'antibodyproductprice': 0.00,
                'antibodyproductname': false,
                'totalamount': 0,
                "partner_code": $('#partner_code').text(),
            }

            $("#buy").click(function() {
                var order = localStorage.getItem("order");
                ajax.jsonRpc("/services/buy-covid19-patientinfo", 'call', {
                    'order': order,
                })
            })

            function antibodyDomCheck(antibodyproductPrice, antibodyProductMembersPrice) {
                if (isCheckedPcr() && !isCheckedTravel()) {
                    addToOrder(products, "COVID-19-PCR2", true)
                    var productPrices = calculatePrice(products, "COVID-19-PCR2")
                    let productTotalPrice = productPrices.totalprice + antibodyproductPrice
                    let productMembersTotalPrice = productPrices.membersPrice + antibodyProductMembersPrice
                    displayPrice(productTotalPrice, productMembersTotalPrice)

                } else if (isCheckedPcr() && isCheckedTravel()) {
                    // PCR and travel selected
                    addToOrder(products, "COVID-19-PCR", true)
                    var productPrices = calculatePrice(products, "COVID-19-PCR")
                    let productTotalPrice = productPrices.totalprice + antibodyproductPrice
                    let productMembersTotalPrice = productPrices.membersPrice + antibodyProductMembersPrice
                    displayPrice(productTotalPrice, productMembersTotalPrice)

                } else if (isCheckedAntigen() && isCheckedTravel()) {
                    //antigen and travel selected
                    addToOrder(products, "COVID-19-ANTIGEN", true)
                    var productPrices = calculatePrice(products, "COVID-19-ANTIGEN")
                    let productTotalPrice = productPrices.totalprice + antibodyproductPrice
                    let productMembersTotalPrice = productPrices.membersPrice + antibodyProductMembersPrice
                    displayPrice(productTotalPrice, productMembersTotalPrice)

                } else if (isCheckedAntigen() && !isCheckedTravel()) {
                    //antigen and travel selected
                    addToOrder(products, "COVID-19-ANTIGEN2", true)
                    var productPrices = calculatePrice(products, "COVID-19-ANTIGEN2")
                    let productTotalPrice = productPrices.totalprice + antibodyproductPrice
                    let productMembersTotalPrice = productPrices.membersPrice + antibodyProductMembersPrice
                    displayPrice(productTotalPrice, productMembersTotalPrice)

                } else {
                    //only antigen selected
                    addToOrder(products, "ANTIBODY", true)
                    var productPrices = calculatePrice(products, "ANTIBODY")
                    let productTotalPrice = productPrices.totalprice + antibodyproductPrice
                    let productMembersTotalPrice = productPrices.membersPrice + antibodyProductMembersPrice
                    displayPrice(productTotalPrice, productMembersTotalPrice)
                }
            }

            //pcr is selected
            $('#testtype_option_id').change(function() {
                let order = JSON.parse(localStorage.getItem("order"))
                if (isCheckedPcr()) {
                    $('#testtype_antigen_option_id').prop('checked', false);
                    $('#is_anti_body').prop('checked', false);
                    $('#is_international_travel').prop('checked', false);
                    order = addToOrder(products, "COVID-19-PCR2", false);
                    var prices = calculatePrice(products, "COVID-19-PCR2")
                    displayPrice(prices.totalprice, prices.membersPrice)
                    $("#note_for_antigen").addClass("d-none");
                    order["isPcrSelected"] = true
                    order["isAntigenSelected"] = false
                    localStorage.setItem("order", JSON.stringify(order))
                    console.log('PCR IS SELECTED ==> !!!', order)


                } else {
                    removeFromOrder(false)
                    order["isPcrSelected"] = false
                    localStorage.setItem("order", JSON.stringify(order))
                    console.log('PCR IS Not SELECTED ')
                }
            });

            $('#testtype_antigen_option_id').change(function() {
                let order = JSON.parse(localStorage.getItem("order"))
                if (isCheckedAntigen()) {
                    $('#testtype_option_id').prop('checked', false);
                    $('#is_anti_body').prop('checked', false);
                    $('#is_international_travel').prop('checked', false);
                    order = addToOrder(products, "COVID-19-ANTIGEN2", false);
                    var prices = calculatePrice(products, "COVID-19-ANTIGEN2");
                    displayPrice(prices.totalprice, prices.membersPrice)
                    $("#note_for_antigen").removeClass("d-none");
                    order["isAntigenSelected"] = true
                    order["isPcrSelected"] = false
                    console.log("Antigen is Selected..!! ==>", order)
                } else {
                    order["isAntigenSelected"] = false
                    order["isPcrSelected"] = true
                    localStorage.setItem("order", JSON.stringify(order))
                }
            });

            var antibodyProductPrices = calculatePrice(products, "ANTIBODY")
            var antibodyproductPrice = antibodyProductPrices.totalprice
            var antibodyProductMembersPrice = antibodyProductPrices.membersPrice

            $('#is_anti_body').change(function() {
                if (isCheckedAntibody()) {
                    $('#is_international_travel').prop('checked', false);
                    console.log('anti price is ', antibodyproductPrice)
                    antibodyDomCheck(antibodyproductPrice, antibodyProductMembersPrice);
                } else {
                    antibodyDomCheck(0, 0)
                    removeFromOrder(true)
                }
            });
            /// anti body ends here


            $('#is_international_travel').change(function() {
                if (isCheckedTravel()) {
                    //if pcr is checked
                    if (isCheckedPcr() && isCheckedAntibody()) {
                        addToOrder(products, "COVID-19-PCR", true)
                        var productPrices = calculatePrice(products, "COVID-19-PCR")
                        let productTotalPrice = productPrices.totalprice + antibodyproductPrice
                        let productMembersTotalPrice = productPrices.membersPrice + antibodyProductMembersPrice
                        displayPrice(productTotalPrice, productMembersTotalPrice)
                    } else if (isCheckedAntigen() && isCheckedAntibody()) {
                        // antigen is selected
                        addToOrder(products, "COVID-19-ANTIGEN", true)
                        var productPrices = calculatePrice(products, "COVID-19-ANTIGEN")
                        let productTotalPrice = productPrices.totalprice + antibodyproductPrice
                        let productMembersTotalPrice = productPrices.membersPrice + antibodyProductMembersPrice
                        displayPrice(productTotalPrice, productMembersTotalPrice)

                    } else if (isCheckedPcr() && !isCheckedAntibody()) {
                        console.log('testing')
                        addToOrder(products, "COVID-19-PCR", false)
                        var productPrices = calculatePrice(products, "COVID-19-PCR")
                        displayPrice(productPrices.totalprice, productPrices.membersPrice)
                    } else if (isCheckedAntigen() && !isCheckedAntibody()) {
                        addToOrder(products, "COVID-19-ANTIGEN", false)
                        var productPrices = calculatePrice(products, "COVID-19-ANTIGEN")
                        displayPrice(productPrices.totalprice, productPrices.membersPrice)
                    } else if (displayPrice(0)) {
                        addToOrder(products, "ANTIBODY", true)
                        var productPrices = calculatePrice(products, "ANTIBODY")
                        displayPrice(productPrices.totalprice, productPrices.membersPrice)
                    } else {
                        order = {}
                        displayPrice(0)
                    }
                } else {
                    if (isCheckedPcr() && isCheckedAntibody()) {
                        addToOrder(products, "COVID-19-PCR2", true)
                        var productPrices = calculatePrice(products, "COVID-19-PCR2")
                        let productTotalPrice = productPrices.totalprice + antibodyproductPrice
                        let productMembersTotalPrice = productPrices.membersPrice + antibodyProductMembersPrice
                        displayPrice(productTotalPrice, productMembersTotalPrice)

                    } else if (isCheckedAntigen() && isCheckedAntibody()) {
                        addToOrder(products, "COVID-19-ANTIGEN2", true)
                        var productPrices = calculatePrice(products, "COVID-19-ANTIGEN2")
                        let productTotalPrice = productPrices.totalprice + antibodyproductPrice
                        let productMembersTotalPrice = productPrices.membersPrice + antibodyProductMembersPrice
                        displayPrice(productTotalPrice, productMembersTotalPrice)

                    } else if (isCheckedAntigen() && !isCheckedAntibody()) {
                        addToOrder(products, "COVID-19-ANTIGEN2", false)
                        var productPrices = calculatePrice(products, "COVID-19-ANTIGEN2")
                        displayPrice(productPrices.totalprice, productPrices.membersPrice)
                    } else if (isCheckedPcr() && !isCheckedAntibody()) {
                        addToOrder(products, "COVID-19-PCR2", false)
                        var productPrices = calculatePrice(products, "COVID-19-PCR2")
                        displayPrice(productPrices.totalprice, productPrices.membersPrice)
                    }
                }
            });
        }


        if (url.indexOf(startPage) != -1 || url.startsWith(covid19Pcr1) || url.startsWith(covid19Pcr2)) {
            console.log("Covid related shown!")
            localStorage.setItem("order", null)
            localStorage.setItem("data", null)
            localStorage.setItem("booking", null)
            localStorage.setItem("cif_data", null)
            localStorage.setItem("hscData", null)


            // MAIN FUNCTION
            ajax.jsonRpc("/covid/params", 'call', {})
                .then(function(params) {
                    processOrder(params)
                    let order = JSON.parse(localStorage.getItem("order"))
                    order['isPcrSelected'] = true;
                    localStorage.setItem("order", JSON.stringify(order));
                });
            //// MAIN function ends here;
        }
        $("#addperson").on('shown.bs.modal', function() {
            ajax.jsonRpc("/covid/params", 'call', {})
                .then(function(params) {
                    processOrder(params)
                });
        });

        $('.verify_promo_code').on('click', function(ev) {
            var code = $("input[name='promo_code']").val();
            ajax.jsonRpc("/covid/params", 'call', { code: code })
                .then(function(params) {
                    processOrder(params);
                    if (params && params.promo) {
                        $("input[name='promo_code']").attr('readonly', 1);
                        alert('Promo Applied Successfully');
                    } else {
                        alert('Promo Code Wrong!');
                    }
                });
        });
    });
});