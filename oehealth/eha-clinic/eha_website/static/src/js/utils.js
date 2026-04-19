/**
 * Utility module for Eha website
 *
 **/

// Function to format number as Commas
function formatCurrency(value) {
    return value.toString().replace(/\D/g, "").replace(/\B(?=(\d{3})+(?!\d))/g, ",")
}

function validateEmail(email) {
    if (email.length && email.match(/.+@.+/)) {
        return true
    }
    return false
}

function validatePhone(phone) {
    //remove empty spaces
    _phone = phone.trim().replace(/\s/g, '')
    var phoneRegex = /^\+[0-9]{1,3}\d{10}$/gm
    if (phoneRegex.test(_phone)) {
        return true;
    }
    return false;
}

function wrongCaptcha(response) {
    console.log(response);
    if (document.getElementById('created')) {
        return false;
    }
    var elem = document.createElement("span");
    var t = document.createTextNode("Invalid reCAPTCHA click the box above to verify that you are human.");
    elem.style = "color:red;font-size:10px;margin-left:12px"
    elem.id = "created";
    elem.appendChild(t);
    parent.appendChild(elem);
    return false;
}

var correctCaptcha = function (response) {
    console.log(response);
    return true;
};

function getCaptcha() {
    var response = document.getElementById('g-recaptcha-response').value;
    var parent = document.getElementById("reload");
    if (document.getElementById('created') && response == "") {
        return false;
    } else if (document.getElementById('created') && response != "") {
        return true;
    }
    var elem = document.createElement("span");
    var t = document.createTextNode("Invalid reCAPTCHA click the box above to verify that you are human.");
    elem.style = "color:red;font-size:10px;margin-left:12px"
    elem.id = "created";
    if (response == "") {
        elem.appendChild(t);
        parent.appendChild(elem);
        return false;
    }
    return true;
}