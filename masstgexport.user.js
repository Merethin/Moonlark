// ==UserScript==
// @name         Moonlark Mass TG Export
// @namespace    http://tampermonkey.net/
// @version      2025-05-23
// @description  Save NationStates recruitment telegram data
// @author       Merethin
// @match        https://*.nationstates.net/*page=tg/tgid=*
// @icon         https://www.google.com/s2/favicons?sz=64&domain=nationstates.net
// @grant        none
// ==/UserScript==

// Clear all custom warning boxes shown by this script.
function clearWarnings()
{
    const elements = document.getElementsByClassName("moonlark-warning");
    while(elements.length > 0){
        elements[0].parentNode.removeChild(elements[0]);
    }
}

// Remove all previous warning boxes and show a new one with the specified text.
function showWarning(warning)
{
    clearWarnings();
    var container = document.createElement('div');
    var label = document.createElement('p');
    label.innerText = "Moonlark Warning: " + warning;
    label.style.fontSize = "16px";
    label.style.margin = "5px";
    container.style.backgroundColor= "orange";
    container.style.padding = "5px";
    container.classList.add("moonlark-warning");
    container.appendChild(label);
    document.querySelector(".tgprefbar").insertAdjacentElement('afterend', container);
}

// Make a nation name URL-compatible by removing (replacing, actually) spaces and uppercase letters
function normalizeNationName(name)
{
    return name.toLowerCase().replace(/ /g, '_');
}

(function() {
    'use strict';

    // Obtain the current Telegram ID by parsing the links at the bottom of the telegram (Conversation, Raw, etc.)
    const tglink1 = document.getElementById("tgmodelinks").children[0].href;
    const regex = /https?:\/\/(?:fast|www)\.nationstates\.net\/.*page=tg\/tgid=([0-9]+).*/y;
    const tgid = regex.exec(tglink1)[1];

    console.log("current telegram id: " + tgid);

    // Insert the script buttons
    const buttonExpandRep = document.createElement("button");
    const buttonExpandRec = document.createElement("button");
    const buttonExpandDel = document.createElement("button");
    const buttonSave = document.createElement("button");

    const banner = document.getElementById("banner");
    banner.append(buttonExpandRep);
    banner.append(buttonExpandRec);
    banner.append(buttonExpandDel);
    banner.append(buttonSave);

    buttonExpandRep.id = "moonlark-expand-rep";
    buttonExpandRep.style = "position: relative; bottom:25px;";
    buttonExpandRep.innerHTML = "Expand Report";
    buttonExpandRep.addEventListener("click", expandReport);

    buttonExpandRec.id = "moonlark-expand-rec";
    buttonExpandRec.style = "position: relative; bottom:25px;";
    buttonExpandRec.innerHTML = "Expand Recruited";
    buttonExpandRec.addEventListener("click", expandRecruited);

    buttonExpandDel.id = "moonlark-expand-del";
    buttonExpandDel.style = "position: relative; bottom:25px;";
    buttonExpandDel.innerHTML = "Expand Delivered";
    buttonExpandDel.addEventListener("click", expandDelivered);

    buttonSave.id = "moonlark-save";
    buttonSave.style = "position: relative; bottom:25px;";
    buttonSave.innerHTML = "Save Data";
    buttonSave.addEventListener("click", saveData);

    function expandReport() {
        const masstgreport = document.querySelector(".masstgreport");
        if(masstgreport == null) {
            showWarning("Unable to expand Mass TG report! This only works on mass telegrams sent by your nation.");
            return;
        }
        masstgreport.click();
        clearWarnings();
    }

    function expandDelivered() {
        const tgexpand = document.getElementById("tgreportexpand-" + tgid + "-0")
        if(tgexpand == null) {
            showWarning("Unable to expand list of recipients! Perhaps you have forgotten to click 'Expand Report'.");
            return;
        }
        tgexpand.click();
        clearWarnings();
    }

    function expandRecruited() {
        const tgexpand = document.getElementById("tgreportexpand-" + tgid + "-recruit")
        if(tgexpand == null) {
            showWarning("Unable to expand list of converted recipients! Perhaps you have forgotten to click 'Expand Report'.");
            return;
        }
        tgexpand.click();
        clearWarnings();
    }

    // Compile all Mass TG data on the current page into a JSON object and export that.
    function saveData() {
        var masstgdata = new Object();

        masstgdata.tgid = parseInt(tgid, 10); // Telegram ID
        masstgdata.generatedAt = Math.floor(Date.now() / 1000); // When this JSON report was generated
        masstgdata.createdAt = parseInt(document.querySelector("a.tgsentline").children[0].dataset.epoch, 10); // When the telegram template was originally created

        masstgdata.nation = normalizeNationName(document.querySelector(".tg_headers").querySelector("span.nname").innerText); // Nation sending the TG

        // If a "category" parameter has been provided, save that.
        const categoryRegex = /https?:\/\/(?:fast|www)\.nationstates\.net\/tgcategory=(.+)\/page=tg\/tgid=(?:[0-9]+).*/y;
        const result = categoryRegex.exec(window.location.href);
        if(result != null) {
            masstgdata.category = result[1];
        }

        // Set the telegram type: "api", "template", or "generic" for Mass TGs sent without a template
        const tgheader = document.querySelector(".tg_headers").innerText;
        if(tgheader.search("tag: api") != -1) {
            masstgdata.type = "api";
        } else if (tgheader.search("tag: template") != -1) {
            masstgdata.type = "template";
        } else {
            masstgdata.type = "generic";
        }

        const tgreportok = document.querySelector("li.tgreport-ok");
        if(tgreportok == null) {
            showWarning("Make sure you have clicked all 'Expand' buttons before trying to save the report!");
            return;
        }

        // Query the amount of telegrams delivered
        masstgdata.delivered = parseInt(tgreportok.children[1].querySelector("strong").innerText.replace(/,/g, ''), 10);

        const tgreportsrec = document.querySelectorAll("li.tgreport-recruit");
        if(tgreportsrec.length == 0) {
            showWarning("Make sure you have clicked all 'Expand' buttons before trying to save the report!");
            return;
        }

        // Query the amount of nations recruited (and if over 1000 delivered, nations who read the TG). Recruit and read rates can be calculated again.
        for(var i = 0; i < tgreportsrec.length; i++) {
            const report = tgreportsrec[i];
            const elements = report.querySelectorAll("strong");
            if(report.innerText.search("Read") != -1) {
                masstgdata.readCount = parseInt(elements[0].innerText.replace(/,/g, ''), 10);
            } else {
                masstgdata.recruitCount = parseInt(elements[0].innerText.replace(/,/g, ''), 10);
            }
        }

        const recruitsBox = document.getElementById("tgreportexpandbox-" + tgid + "-recruit");
        if(recruitsBox == null) {
            showWarning("Make sure you have clicked all 'Expand' buttons before trying to save the report!");
            return;
        }

        // Save the actual nations recruited, the time at which they were recruited, as well as whether they're CTE now or not
        masstgdata.recruits = new Array();
        const allRecruits = recruitsBox.querySelectorAll("li");
        for(i = 0; i < allRecruits.length; i++) {
            const recruit = allRecruits[i];

            const recruitObject = new Object();
            recruitObject.cte = false;

            var name = recruit.querySelector("span.nname");
            if(name == null) {
                name = recruit.querySelector("span.nnameblock");
                recruitObject.cte = true;
            }

            recruitObject.name = normalizeNationName(name.innerText);
            recruitObject.timestamp = parseInt(recruit.querySelector("time").dataset.epoch, 10);

            masstgdata.recruits.push(recruitObject);
        }

        const recipientsBox = document.getElementById("tgreportexpandbox-" + tgid + "-0");
        if(recipientsBox == null) {
            showWarning("Make sure you have clicked all 'Expand' buttons before trying to save the report!");
            return;
        }

        // Save a list of all nations who have received our telegram
        masstgdata.recipients = new Array();
        const allRecipients = recipientsBox.querySelectorAll("a");
        for(i = 0; i < allRecipients.length; i++) {
            masstgdata.recipients.push(normalizeNationName(allRecipients[i].innerText));
        }

        clearWarnings();

        // Use octet-stream as MIME so that it's downloaded instead of displayed in the browser (as application/json would do)
        const file = new File([JSON.stringify(masstgdata, null, "\t")], tgid + '.json', { type: 'application/octet-stream' });

        // Export as a JSON file which should be saved to the user's download folder or trigger a save popup
        const objectUrl = window.URL.createObjectURL(file);
        window.open(objectUrl);
    }
})();