odoo.define("eha_website_sale.website_sale", function (require) {
  "use strict";

  var publicWidget = require("web.public.widget");
  var ajax = require("web.ajax");

  publicWidget.registry.WebsiteSale.include({
    _onClickSubmit: function (ev, forceSubmit) {
      if (
        $(ev.currentTarget).is("#add_to_cart, #products_grid .a-submit") &&
        !forceSubmit
      ) {
        return;
      }
      var $aSubmit = $(ev.currentTarget);
      if (!ev.isDefaultPrevented() && !$aSubmit.is(".disabled")) {
        ev.preventDefault();
        $aSubmit.closest("form").submit();
      }
      if ($aSubmit.hasClass("a-submit-disable")) {
        $aSubmit.addClass("disabled");
      }
      if ($aSubmit.hasClass("a-submit-loading")) {
        var loading = '<span class="fa fa-cog fa-spin"/>';
        var fa_span = $aSubmit.find('span[class*="fa"]');
        if (fa_span.length) {
          fa_span.replaceWith(loading);
        } else {
          $aSubmit.append(loading);
        }
      }
    },

    init: function () {
      this._super.apply(this, arguments);

      /// determines if user is logging in for the first time without branch

      let isBranchSelected = localStorage.getItem("isBranchSelected");
      if (isBranchSelected === null) {
        $("#branchModal").modal("show");
        console.log("show true");
      } else {
        console.log("not show true");
      }
      let currentDropdownText = localStorage.getItem("currDropdownText");
      $("#dropdownMenuButtonBranch").text(currentDropdownText);
      $("#dropdownMenuButtonBranch").val(currentDropdownText);


      this._changeCartQuantity = _.debounce(
        this._changeCartQuantity.bind(this),
        500
      );
      this._changeCountry = _.debounce(this._changeCountry.bind(this), 500);

      this.isWebsite = true;

      delete this.events[
        "change .main_product:not(.in_cart) input.js_quantity"
      ];
      delete this.events["change [data-attribute_exclusions]"];
    },

    start: function () {
      this._super.apply(this, arguments);
      var query = this.getQueryStringObject();
      let currentDropdownText = localStorage.getItem("currDropdownText");
      let isBranchSelected = localStorage.getItem("isBranchSelected");
      if (isBranchSelected === null) {
        console.log("Branch Modal showing ... ");
        $("#branchModal").modal("show");
      }
      $("#dropdownMenuButtonBranch").text(currentDropdownText);
      $("#dropdownMenuButtonBranch").val(currentDropdownText);
      if (query && query.from_login) {
        $("a.js_edit_address").trigger("click");
      }
    },
    getQueryStringObject: function () {
      return Object.fromEntries(new URLSearchParams(location.search));
    },
  });

  $("a[name=cart_add]").click(function (ev) {
    let productId = ev.target.dataset.id;
    console.log("Selected Product:", productId);
    ajax
      .jsonRpc("/shop/cart/update_json", "call", {
        product_id: productId,
        add_qty: 1,
        set_qty: 0,
      })
      .then(function (is_valid) {
        if (is_valid) {
          $(".toast").removeClass("d-none");
          $(".toast").toast("show");
        } else {
          alert("An error occur while adding item to the cart!");
        }
      });
  });

  $(function () {
    $(".branch_element_id a span").click(function () {
      console.log("This is the text ", $(this).text());
      $("#dropdownMenuButtonBranch").text($(this).text()).trigger("change");
      $("#dropdownMenuButtonBranch").val($(this).text()).trigger("change");
      localStorage.setItem("currDropdownText", $(this).text());
    });

    $(".branch-div").click(function () {
      let selectedBranch = $(this).attr("id");
      let selectedBranchName = $(this).attr("name");
      localStorage.setItem("currBranchId", selectedBranch);
      localStorage.setItem("currDropdownText", selectedBranchName);
      $("#select-branch-btn").prop("disabled", false);
      $(".branchCheckbox").prop("checked", false);
      $(`input[name="${selectedBranchName}"`).prop("checked", true);
      console.log($(".branch-div input[type=radio]").prop("checked"));
    });

    // when a branch is selected, click on the location button, if will redirect using the branch pricelist
    $("#select-branch-btn").click(function () {
      localStorage.setItem("isBranchSelected", true);
      $("#branchModal").modal("hide");
    });
  });

  publicWidget.registry.WebsiteSaleLayout.include({
    /**
     * @private
     * @param {Event} ev
     */
    _onApplyShopLayoutChange: function (ev) {
      var switchToList = $(ev.currentTarget)
        .find(".o_wsale_apply_list input")
        .is(":checked");
      // console.log('2 List or Grid clicked')
      if (switchToList) {
        console.log("22 List or Grid clicked");
        if ($("#layout_mode_text").text() == "list") {
          $("#layout_mode_text").text("grid");
        } else {
          $("#layout_mode_text").text("list");
        }
      }

      if (!this.editableMode) {
        this._rpc({
          route: "/shop/save_shop_layout_mode",
          params: {
            layout_mode: switchToList ? "list" : "grid",
          },
        });
      }
      var $grid = this.$("#products_grid");
      // Disable transition on all list elements, then switch to the new
      // layout then reenable all transitions after having forced a redraw
      // TODO should probably be improved to allow disabling transitions
      // altogether with a class/option.
      $grid.find("*").css("transition", "none");
      $grid.toggleClass("o_wsale_layout_list", switchToList);
      void $grid[0].offsetWidth;
      $grid.find("*").css("transition", "");
      window.location.reload();
    },
  });
});
