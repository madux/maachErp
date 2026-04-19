odoo.define("eha_telehealth.telehealth_booking", function (require) {
  "use strict";
  require("web.dom_ready");

  var ajax = require("web.ajax");
  var nav_tabs_link_1 = $("#nav_tabs_link_1");
  var nav_tabs_link_2 = $("#nav_tabs_link_2");
  var nav_tabs_link_3 = $("#nav_tabs_link_3");
  var saveNameBtn = $("#telehealth-save");
  let waiting_label = $("#waiting_label");
  var appointmentDate = $("input[name='datepicker2']");
  var telehealthConfirmSlot = $("#telehealth-confirm-date");
  var selectedTimeSlot;
  var SelectedTime;
  var locationId = $("input[name='location']").attr("id");
  var serviceId = $("input[name='booking_service']").attr("id");
  var telehealthPriceTotal = $("#telehealth-price-total");
  let telehealthNoteDoctor = $("#telehealth-note-to-doctor");
  let backtoPatientDetailsBtn = $("#telehealth-back-to-patient-details");
  let teleHealthNote = $("#telehealth-leave-note");
  let backtoDateTimeBtn = $("#telehealth-back-to-date-time");
  let insuranceCode = $("#insurance_code");
  let amountTotal;
  let bookingDate;
  let bookingTime;

  let clientId;
  let client;
  let startDate;
  var startTime;
  var count;
  let SimplybookserviceId;
  let SimplybookperformerId;
  let SimplybookSimplybookLocationId; // = $("#simplybook_location").attr("id");
  let savebtnHtml = saveNameBtn.html();
  let waiting_labelhtml = $("#waiting_label").html();
  let paymentOption = $(".telehealth-payment-option");

  function hideElements() {
    $("#time-block").hide();
    // $('#displaytime').hide();
    $("#dateFrom").hide();
    $("#dateTo").hide();
    // $('#select_event_id').hide();
    // $('#select_unit_id').hide();
  }

  function renderSimplybookOptions() {
    saveNameBtn.attr("disabled", true);
    saveNameBtn.html('<i class="fa fa-spinner fa-spin"></i> Please wait ...');
    waiting_label.html(
      '<i class="fa fa-spinner fa-spin"> </i> Please wait ... '
    );
    ajax
      .jsonRpc("/simplybookme/params", "call", {})
      .then(function (params) {
        //catch neccessary varibales for use later
        var telehealth_location_id = params["telehealth_location_id"];
        var telehealth_service_id = params["telehealth_service_id"];
        var telehealth_performer_id = params["telehealth_performer_id"];

        var ADMINLOGIN = params["admin_login"];
        var ADMINPASSWORD = params["admin_password"];
        var url = params["url"];
        var CompanyLogin = params["company_login"];
        console.log(
          `Company login --> ${CompanyLogin} = url --> ${url} ==password --> ${ADMINPASSWORD}  ==adminlogin --> ${ADMINLOGIN} ==location --> ${telehealth_location_id}`
        );
        var client = false;
        // login to simplybook
        var loginClient = new JSONRpcClient({
          url: url + "/login",
          onerror: function (error) {
            console.log("SimplyBookme Client Error: ", error);
          },
        });
        //retrieve token
        var Usertoken = loginClient.getUserToken(
          CompanyLogin,
          ADMINLOGIN,
          ADMINPASSWORD
        );
        //create admin client handle
        client = new JSONRpcClient({
          url: url + "/admin/",
          headers: {
            "X-Company-Login": CompanyLogin,
            "X-User-Token": Usertoken,
          },
          onerror: function (error) {
            console.log(`"SimplyBookme Admin Auth Error ${error}"`);
          },
        });
        var buildBookingLocations = function () {
          var locations = client.getLocationsList();
          var services = client.getEventList();
          var performers = client.getUnitList();

          //build location
          jQuery("#simplybook_location").append(
            jQuery(
              '<option value="' +
                Number(telehealth_location_id) +
                '" selected>' +
                locations[Number(telehealth_location_id)].name +
                "</option>"
            )
          );
          SimplybookSimplybookLocationId = Number(telehealth_location_id);
          SimplybookserviceId = Number(telehealth_service_id);
          SimplybookperformerId = Number(telehealth_performer_id);
          //build events
          $('input[name="event_id"]').val(SimplybookserviceId);
          $('input[name="unit_id"]').val(SimplybookperformerId);
          $("#simplybook_location").change(function (ev) {
            var LocId = $(this).val();
            $("#datepicker2").val("");
            $("#starttime").empty();
            if (LocId == Number(telehealth_location_id)) {
              SimplybookSimplybookLocationId = Number(telehealth_location_id);
              SimplybookserviceId = Number(telehealth_service_id);
              SimplybookperformerId = Number(telehealth_performer_id);
            }
            //build events
            $('input[name="event_id"]').val(SimplybookserviceId);
            $('input[name="unit_id"]').val(SimplybookperformerId);
          });
        }; //end function
        var buildCalendar = function () {
          SimplybookserviceId = $('input[name="event_id"]').val();
          SimplybookperformerId = $('input[name="unit_id"]').val();
          // console.log("Performer selected ==>", SimplybookperformerId)
          // Used this to render time as a select option
          $("#displaytime").change(function () {
            SelectedTime = $(this).val();
          });
          // display calendar
          var firstWorkingDay = client.getFirstWorkingDay(
            SimplybookperformerId
          );
          console.log("Its first day was ==>", firstWorkingDay);
          var workCalendar = {};
          jQuery("#datepicker2").datepicker({
            onChangeMonthYear: function (year, month, inst) {
              workCalendar = client.getWorkCalendar(
                year,
                month,
                SimplybookperformerId
              );
              jQuery("#datepicker2").datepicker("refresh");
            },
            minDate: new Date(),
            beforeShowDay: function (date) {
              var year = date.getFullYear();
              var month = ("0" + (date.getMonth() + 1)).slice(-2);
              var day = ("0" + date.getDate()).slice(-2);
              var date = year + "-" + month + "-" + day;
              if (typeof workCalendar[date] != "undefined") {
                if (parseInt(workCalendar[date].is_day_off) == 1) {
                  return [false, "", ""];
                }
              }
              return [true, "", ""];
            },
          });
          var firstWorkingDateArr = firstWorkingDay.split("-");
          workCalendar = client.getWorkCalendar(
            firstWorkingDateArr[0],
            firstWorkingDateArr[1],
            SimplybookperformerId
          );
          $("#datepicker2").datepicker("refresh");
          // Handle date selection
          var counts = 1; // How many slots book
          count = counts;
          function formatDate(date) {
            var year = date.getFullYear();
            var month = ("0" + (date.getMonth() + 1)).slice(-2);
            var day = ("0" + date.getDate()).slice(-2);
            return year + "-" + month + "-" + day;
          }
          function drawMatrix(matrix) {
            jQuery("#starttime").empty();
            if (matrix.length > 0) {
              jQuery("#busy-simplybook").addClass("d-none");
              jQuery("#showtimelabel-simplybook").removeClass("d-none");
            }
            var SortDuplicateMatrix = _.shuffle(matrix).slice(0, 20).sort();
            var timeItems = [];
            _.each(SortDuplicateMatrix, function (e) {
              var suffix = parseInt(e.slice(0, 2)) >= 12 ? " PM" : " AM";
              var formatHour =
                ((parseInt(e.slice(0, 2)) + 11) % 12) +
                1 +
                e.slice(2, 5) +
                suffix;
              jQuery("#starttime").append(
                jQuery(
                  '<button type="button" id="btn-time" class="btn mr-1 mb-1 btn-outline-primary btn-sm o_default_snippet_text" data-time="' +
                    e.slice(0, 5) +
                    '">' +
                    formatHour +
                    "</button>"
                )
              );
              timeItems.push(formatHour);
            });
            console.log("TIMES = DISPLAYED IN AM/PM", timeItems);
            if (timeItems.length < 1) {
              $("#busy-simplybook").removeClass("d-none");
              $("#showtimelabel-simplybook").addClass("d-none");
            }
            $("#starttime button").click(function () {
              startTime = jQuery(this).data("time");
              selectedTimeSlot = $(this).data("id") || null;
              var DisplayTime = jQuery("#displaytime").val(startTime);
              console.log(
                "Date Time selected ==> " +
                  startDate +
                  " - " +
                  "startTime" +
                  DisplayTime
              );
              $("#starttime button").removeClass("active");
              $(this).addClass("active");
            });
          }
          $("#datepicker2").datepicker("option", "onSelect", function () {
            startDate = formatDate(jQuery(this).datepicker("getDate"));
            jQuery("#time-block").show();
            jQuery("#dateFrom, #dateTo").val(startDate);
            startDate = startDate;
            var startMatrixx = client.getStartTimeMatrix(
              startDate,
              startDate,
              SimplybookserviceId,
              SimplybookperformerId,
              count
            );
            drawMatrix(startMatrixx[startDate]);
          });
          waiting_label.html(waiting_labelhtml);
        }; //end buildCalendar
        //initialize location and calendar
        new buildBookingLocations();
        new buildCalendar();
        saveNameBtn.attr("disabled", false);
        saveNameBtn.html(savebtnHtml);
      })
      .catch(function (e) {
        console.log("Could not connect because of this issue===> ", e);
      });
  }

  // Save the details of the patient in the server-side session
  function saveName(ev) {
    ev.preventDefault();
    localStorage.removeItem("telehealthPatient");
    localStorage.removeItem("telehealthPartner");
    let firstName = $("input[name='firstname']");
    let lastName = $("input[name='lastname']");
    let middleName = $("input[name='middlename']");
    let gender = $("select[name='gender']");
    let email = $("input[name='email']");
    let dob = $("input[name='dob']");
    let phone = $("input[name='phone']");
    let patientId = $("input[name='patientID']");
    let StateId = $("#patient-state");
    if (
      !(
        firstName.val() &&
        lastName.val() &&
        email.val() &&
        dob.val() &&
        phone.val() &&
        gender.val()
      )
    ) {
      alert(
        "Missing a compulsory field \nPlease check that you filled the firstname, lastname, date of birth, phone and gender"
      );
      return false;
    }
    ajax
      .rpc("/telehealth/patients", {
        params: {
          first_name: firstName.val(),
          last_name: lastName.val(),
          middle_name: middleName.val(),
          gender: gender.val(),
          dob: dob.val(),
          email: email.val(),
          phone: phone.val(),
          patient_id: patientId.val(),
          state_id: StateId.val(),
        },
      })
      .then((data) => {
        renderSimplybookOptions();
        localStorage.setItem("telehealthPartner", data.partner_id);
        localStorage.setItem("telehealthPatient", data.patient_id);
      })
      .catch((error) => console.log(error));
    return nav_tabs_link_2.tab("show");
  }

  function setSlotsOnPage(slots) {
    $("#times").empty();
    if (slots.length > 0) {
      $("#busy").addClass("d-none");
      $("#showtimelabel").removeClass("d-none");
    }
    let timeItems = [];
    slots.forEach(function (e) {
      let Hour = e.name.split(":")[0];
      let intergerHour = Number(Hour);
      let formattedTimeSlot = `${
        intergerHour > 12 ? Math.floor(intergerHour % 12) : intergerHour
      }:${e.name.split(":")[1]} ${intergerHour >= 12 ? " PM" : " AM"}`;
      $("#times").append(
        $(
          `<button type="button" data-id=${e.id} class="btn mr-1 mb-1 btn-outline-primary btn-sm o_default_snippet_text">${formattedTimeSlot}</button>`
        )
      );
      timeItems.push(formattedTimeSlot);
    });
    if (timeItems.length < 1) {
      $("#busy").removeClass("d-none");
      $("#showtimelabel").addClass("d-none");
    }

    $("#times button").click(function (e) {
      self = this;
      e.preventDefault();
      let previouslySelectedTime = $("#times button.picked");
      if (previouslySelectedTime) {
        $(previouslySelectedTime).removeClass("picked");
      }
      $(self).addClass("picked");
      selectedTimeSlot = $(self).data("id") || null;
      $(self).removeClass("active");
    });
  }

  /**
   * Get time slots for the selected location and date date
   */
  function getTimeslots() {
    let bookingDate = appointmentDate.val();
    ajax
      .rpc(
        `/api/v1/booking/locations/${locationId}/services/${serviceId}/slots`,
        {
          booking_date: bookingDate,
        }
      )
      .then((res) => {
        //save the booking with the slots that are returned
        if (res.status === "200") {
          let slots = res.data.slots.availableSlots;
          $("#time-block").show();
          setSlotsOnPage(slots);
        }
      })
      .catch((error) => console.log("Here is an error" + error));
  }

  // this will save booking in a localStorage for eventual booking after successful payment
  function createBooking(ev) {
    ev.preventDefault();
    let selectedAppointmentDate = appointmentDate.val();
    let selectedTimeSlot = $("#displaytime").val();
    if (!(SimplybookSimplybookLocationId || SimplybookserviceId)) {
      alert("Either a location or service is missing. Please contact EHA");
      return false;
    }
    if (!selectedAppointmentDate) {
      alert("No date was selected");
      appointmentDate.val("");
      return false;
    }
    if (!selectedTimeSlot) {
      alert("Please pick a time");
      return false;
    }
    var clientData = {
      name: $("#client-firstname").val() + "-" + $("#client-lastname").val(),
      email: $("#client-email").val(),
      phone: $("#client-phone").val(),
      patientId: $("#client-patientID").val(),
      state: $("#patient-state").val(),
    };

    // send the details of the booking to the backend
    ajax
      .rpc("/telehealth/booking_details", {
        params: {
          location_id: locationId,
          service_id: serviceId,
          simplybook_service_id: SimplybookserviceId,
          simplybook_location_id: SimplybookSimplybookLocationId,
          simplybook_performer_id: SimplybookperformerId,
          simplybook_date: selectedAppointmentDate,
          simplybook_time: selectedTimeSlot,
          clientData: clientData,
          slot_id: selectedTimeSlot,
          booking_date: selectedAppointmentDate,
          note_for_doctor: teleHealthNote.val(),
        },
      })
      .then((response) => {
        console.log(
          "Feedback from the server for the appointment date and all " +
            typeof response
        );
        ajax
          .rpc(`/telehealth/fees`, {
            telehealthPartner:
              localStorage.getItem("telehealthPartner") !== "null"
                ? localStorage.getItem("telehealthPartner")
                : "",
            telehealthPatient:
              localStorage.getItem("telehealthPatient") !== "null"
                ? localStorage.getItem("telehealthPatient")
                : "",
          })
          .then((res) => {
            amountTotal = res.amount;
            telehealthNoteDoctor.html($("#telehealth-leave-note").val());
            if (Number(amountTotal) === 0) {
              $("#card").hide();
              $("#non-member-confirm-payment").hide();
              $("#member-confirm-booking").show();
            } else {
              $("#card").show();
              $("#non-member-confirm-payment").show();
              $("#member-confirm-booking").hide();
            }
            telehealthPriceTotal.text(amountTotal);
            localStorage.setItem("telehealthPartner", "");
            localStorage.setItem("telehealthPatient", "");
            $("#telehealth-summary-booking-date").text(selectedAppointmentDate);
            $("#telehealth-summary-booking-time").text(selectedTimeSlot);
            nav_tabs_link_3.tab("show");
          });
      });
  }

  function triggerInsuranceDetails() {
    $("#insurance_checkbox").on("click", function (ev) {
      var $this = $(ev.target);
      var insurance_name = $("#insurance_name");
      var insurance_code = $("#insurance_code");
      if ($this.prop("checked")) {
        localStorage.setItem("payment_type", null);
        insurance_name.attr("required", true);
        insurance_code.attr("required", true);
        $("#non-member-confirm-payment").hide();
        $("#member-confirm-booking").show();
        $("#booking-btn").text("Book Now");
      }
    });
  }

  function triggerPaymentDetails() {
    $("#payment_detail_checkbox").on("click", function (ev) {
      var $this = $(ev.target);
      var insurance_name = $("#insurance_name");
      var insurance_code = $("#insurance_code");
      if ($this.prop("checked")) {
        localStorage.setItem("payment_type", true);
        console.log("payment details clicked");
        insurance_name.attr("required", false);
        insurance_code.attr("required", false);
        insurance_name.val("");
        insurance_code.val("");
        $("#non-member-confirm-payment").show();
        $("#member-confirm-booking").hide();
        $("#booking-btn").text("Confirm Booking");
      }
    });
  }

  function changeIsInsurance() {
    // changes
    $("#booking-btn").text("Book Now");
  }

  function goToPatientDetailsTab() {
    nav_tabs_link_1.tab("show");
  }

  function goToDateTimeTab() {
    nav_tabs_link_2.tab("show");
  }
  function postBookingWithoutPayment() {
    let insurance_name = $("#insurance_name");
    let insurance_code = $("#insurance_code");
    let is_insurance = $("#insurance_checkbox");
    if (is_insurance.prop("checked")) {
      if (!insurance_name.val() || !insurance_code.val()) {
        alert("Insurance Name and Code must be provided !!!");
        return false;
      }
    }
    let $btn = $("#booking-btn");
    let $btnHtml = $btn.html();
    $btn.attr("disabled", "disabled");
    $btn.prepend('<i class="fa fa-spinner fa-spin"/> ');
    ajax
      .rpc("/telehealth/register", {
        params: {
          insurance_name: insurance_name.val(),
          insurance_code: insurance_code.val(),
          is_insurance: is_insurance.val(),
        },
      })
      .then((response) => {
        console.log(response);
        $btn.attr("disabled", false);
        $btn.html($btnHtml);
        window.location.href = `/telehealth-final/${response}`;
      });
  }

  function changeSuccessTextLabel() {
    let paymentLabelText = $("#label-for-payment");
    let nonpaymentLabelText = $("#label-for-non-payment");
    let payment_type = localStorage.getItem("payment_type");
    if (payment_type === "null") {
      console.log("Displaying non payment text");
      nonpaymentLabelText.removeClass("d-none");
      paymentLabelText.addClass("d-none");
    } else {
      console.log("Displaying payment text");
      paymentLabelText.removeClass("d-none");
      nonpaymentLabelText.addClass("d-none");
    }
  }

  // Add implementation for clickable area while selecting payment method
  let paymentOptions = $(".telehealth-payment-option");
  paymentOptions.each(function (option) {
    $(this).click(function () {
      let input = $("input", $(this));
      let checked = input.prop("checked");
      input.prop("checked", !checked);
    });
  });
  saveNameBtn.on("click", saveName);
  telehealthConfirmSlot.on("click", createBooking);
  nav_tabs_link_1.on("click", () => false);
  nav_tabs_link_2.click(() => false);
  nav_tabs_link_3.click(() => false);
  backtoPatientDetailsBtn.on("click", goToPatientDetailsTab);
  backtoDateTimeBtn.on("click", goToDateTimeTab);
  insuranceCode.on("change", changeIsInsurance);
  $("#booking-btn").on("click", postBookingWithoutPayment);
  changeSuccessTextLabel();
  triggerPaymentDetails();
  triggerInsuranceDetails();
});
