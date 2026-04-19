odoo.define("helpdesk_extension.dashboard", function (require) {
  "use strict";

  require("web.dom_ready");
  var sAnimation = require("website.content.snippets.animation");

  sAnimation.registry.ehaHelpdesk = sAnimation.Class.extend({
    selector: ".dashboard",
    start: function () {
      var self = this;

      //hide website header and footer when viewing the dashboard
      var pathName = window.location.pathname;
      if (pathName == "/helpdesk/dashboard/") {
        //body.o_connected_user {padding-top: 46px !important;}
        $("body").css({
          "margin-top": "-46px",
        });
        $("header, .footer, .o_main_navbar").hide();
      }

      //initialize the dashboard
      self._refreshDashboard();
      //Refresh the Dashboard every 30 seconds
      var POLL_FREQUENCY = 30000;
      var x = setInterval(function () {
        self._refreshDashboard();
      }, POLL_FREQUENCY);
    },
    inProgress: false,
    _refreshDashboard: function () {
      var self = this;

      if (self.inProgress) {
        return;
      }
      $.ajax({
        url: "/helpdesk/tickets",
        type: "GET",
        beforeSend: function () {
          self.inProgress = true;
        },
      })
        .then(function (data) {
          self._handleResponse(data);
        })
        .fail(function (jxhr, textStatus) {
          // console.error('Request For Helpdesk Tickets Failed ' + textStatus);
          console.log("Request For Helpdesk Tickets Failed " + textStatus);
        })
        .then(function () {
          self.inProgress = false;
        });
    },
    _handleResponse: function (data) {
      var self = this;
      if (data) {
        var row;
        // var teams = JSON.parse(data)
        $.each(data, function (k, v) {
          var room_status =
            v.room_status != "" ? v.room_status.toLowerCase() : "clean";
          var room_type = v.room_type.toLowerCase();
          var room_name = v.room_name;

          if (room_status == "occupied") {
            row += `<tr><td class="room">${room_name}</td><td colspan="6" class="patient"><table>`;
            $.each(v.tickets, function (key, ticket) {
              var patient_id = ticket.patient_id;
              var eval_url = "";
              var patient_uri = `/web?#id=${patient_id}&action=900&model=oeh.medical.patient&view_type=form&menu_id=734`;
              var statusDate = new Date(ticket.status_change_time).getTime();
              var createDate = new Date(ticket.create_date).getTime();
              var time_in_status = self._getCountDown(statusDate);
              var time_in_clinic = self._getCountDown(createDate);
              var ticket_stage = ticket.stage
                ? ticket.stage.toLowerCase()
                : null;
              var ticket_stage2 = ticket.stage;
              var prescription_status_label = "";
              var labtest_status_label = "";
              var lab_result_ready = ticket.lab_result_ready;
              var prescription_ready = ticket.prescription_ready;
              var lab_result_status = ticket.lab_result_status;
              var prescription_status = ticket.prescription_status;
              var is_online_pharmacy = ticket.is_online_pharmacy;
              var highlight_class = "";
              if (is_online_pharmacy) {
                highlight_class = "eha_online_pharmacy";
              }

              //lab result ready is independent of transition and rooms
              if (lab_result_status == "ordered") {
                labtest_status_label = `<i class="fas fa-vial"></i>`;
              } else if (lab_result_status == "in progress") {
                labtest_status_label = `<i class="fas fa-vial status-progress"></i>`;
              } else if (lab_result_status == "ready") {
                labtest_status_label = `<i class="fas fa-vial status-ready"></i>`;
                if (
                  room_type == "waiting room" &&
                  ticket_stage == "waiting for lab results"
                ) {
                  ticket_stage2 = "Lab Result Is Ready";
                }
              } else {
                labtest_status_label = "";
              }

              //prescription ready is independent of transition and rooms
              if (prescription_status == "ordered") {
                prescription_status_label = `<i class="fas fa-file-alt"></i>`;
              } else if (prescription_status == "in progress") {
                prescription_status_label = `<i class="fas fa-file-alt status-progress"></i>`;
              } else if (prescription_status == "ready") {
                prescription_status_label = `<i class="fas fa-file-alt status-ready"></i>`;
                if (
                  (room_type == "pharmacy" &&
                    ticket_stage == "waiting for prescription") ||
                  (room_type == "waiting room" &&
                    ticket_stage == "waiting for prescription")
                ) {
                  ticket_stage2 = "Prescription Is Ready";
                }
              } else {
                prescription_status_label = "";
              }

              if (parseInt(ticket.eval_id) > 0) {
                //prod eval url
                //web?#id=&action=914&active_id=1&model=oeh.medical.evaluation&view_type=form&menu_id=734
                eval_url = `/web#id=${ticket.eval_id}&action=914&active_id=1&model=oeh.medical.evaluation&view_type=form&menu_id=734`;
              } else {
                eval_url = "#";
              }

              row += `<tr class="${highlight_class}">                        
                          <td class="name"> <a href="${patient_uri}" target="_blank"> ${ticket.patient_initial}</a> &nbsp;<a href="${eval_url}" target="_blank"> ${ticket.eval_no}</a></td>
                          <td class="status"> <span class="status-change-time" style="display:none;">${ticket.status_change_time}</span> <span class="time-status">${time_in_status}</span> ${ticket_stage2}</td>
                          <td class="physician">${ticket.clinician}</td>
                          <td class="prescription">${prescription_status_label}</i></td>
                          <td class="test">${labtest_status_label}</td>
                          <td class="time"><i class="fas fa-clock time-clock"></i><span class="create-date" style="display:none;"> </span><span class="time-clinic">${time_in_clinic}</span></td>
                      </tr>`;
            });
            row += `</table></td></tr>`;
          } else if (room_status == "dirty") {
            row += `<tr>
                  <td class="room status-dirty">${room_name}</td>
                  <td colspan="6" class="room-status status-dirty">needs cleaning</td>
                </tr>`;
            //waiting area , pharmacy etc is occupied but no person in it, show it to be cleab
          } else {
            row += `<tr>
                  <td class="room status-clean">${room_name}</td>
                  <td colspan="6" class="room-status status-clean">clean</td>' +
                </tr>`;
          }
        });
        self.$target.find("table.dashboard-table > tbody").html(row);
      }
    },

    _getCountDown: function (inputDate) {
      // Get today's date and time
      var now = new Date().getTime();
      // Find the distance between now and the count down date
      var distance = now - inputDate;
      // Time calculations for days, hours, minutes and seconds
      var days = Math.floor(distance / (1000 * 60 * 60 * 24));
      var hours = Math.floor(
        (distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)
      );
      var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
      var seconds = Math.floor((distance % (1000 * 60)) / 1000);
      minutes = minutes >= 10 ? minutes : "0".concat(minutes.toString());
      var $hours = hours >= 10 ? hours : "0".concat(hours.toString());
      seconds = seconds >= 10 ? seconds : "0".concat(seconds.toString());
      var $days = days >= 10 ? days : "0".concat(days.toString());
      if (days >= 1) {
        return $days + ":" + $hours + ":" + minutes + ":" + seconds;
      }
      if (hours >= 1) {
        return $hours + ":" + minutes + ":" + seconds;
      }
      return minutes + ":" + seconds;
    },
  });
});
