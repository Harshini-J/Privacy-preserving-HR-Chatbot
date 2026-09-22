let userInp;
let userInput;
let sendButton;
let chatBox;
var emp_id;
function load()
{
    userInp = document.getElementById("user-input");
    userInput = userInp.value;
    sendButton = document.getElementById("msg");
    chatBox = document.getElementById("chat-box");
    emp_id = 1005675;
}
function capitalize(val) {
    return String(val).charAt(0).toUpperCase() + String(val).slice(1);
}

function sendMessage() {
    userInput = userInp.value;
    fetch("/chat", {
        method: "POST",
        body: JSON.stringify({ message: userInput, employee_id: emp_id}),
        headers: { "Content-Type": "application/json" }
    })
    .then(response => response.json())
    .then(data => {
        var impWords = data.imp_words;
        resp = data;
        if (data.context === "banned")
        {
            chatBox.innerHTML = `<H1><strong>${data.response}</strong></H1>`;
            userInp.disabled = true;
            userInp.placeholder = "";
            userInp.value = "";
            sendButton.disabled = true;
        }
        else
        {
            for (var i = 0; i < impWords.length; i++)
            {
                let regex1 = new RegExp(`\\b${impWords[i]}\\b`, "g"); // Match whole words only
                let capWord = capitalize(impWords[i]);
                let regex2 = new RegExp(`\\b${capWord}\\b`, "g");
                userInput = userInput.replace(regex1, `<strong>${impWords[i]}</strong>`);
                userInput = userInput.replace(regex2, `<strong>${capWord}</strong>`);
            }
            chatBox.innerHTML += `<p><strong>You:</strong> ${userInput}</p>`;
            chatBox.innerHTML += `<p><strong>Bot:</strong> ${data.response}</p>`;
            document.getElementById("user-input").value = "";
            var context = data.context;
            if (context === "leave-form" || context === "payslip-form")
            {
                userInp.disabled = true;
                userInp.placeholder = "";
                sendButton.disabled = true;
            }
            if (context === "holiday" || context === "payslip")
            {
                userInp.placeholder = "(Y/N)";
            }
            if (context === "")
            {
                userInp.placeholder = "Type a message...";
            }
        }
    });
}

function submitLeave() {
    let dateInp = document.getElementById("start-date");
    let daysInp = document.getElementById("leave-days");
    let typeInp = document.getElementById("leave-type");
    let startDate = dateInp.value;
    let leaveDays = daysInp.value;
    let leaveType = typeInp.value;
    fetch("/leave", {
        method: "POST",
        body: JSON.stringify({date: startDate, days: leaveDays, type: leaveType, employee_id: emp_id}),
        headers: { "Content-Type": "application/json" }
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById("leave-form").remove();
        chatBox.innerHTML += `<p><strong>You:</strong><br><h3>Leave Request Form</h3>Leave Type: ${leaveType}<br>Number of Days: ${leaveDays}<br>Start Date: ${startDate}.</p>`;
        chatBox.innerHTML += `<p><strong>Bot:</strong> ${data.response}</p>`;
        document.getElementById("user-input").value = "";
        userInp.disabled = false;
        userInp.placeholder = "Type a message...";
        sendButton.disabled = false;
    });
}

function submitPayslip() {
    let monthInp = document.getElementById("month");
    let month = monthInp.value;
    fetch("/payslip", {
        method: "POST",
        body: JSON.stringify({month: month, employee_id: emp_id}),
        headers: { "Content-Type": "application/json" }
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById("payslip-form").remove();
        chatBox.innerHTML += `<p><strong>You:</strong><br><h3>Payslip Request Form</h3>Requested Month: ${month}.<br></p>`;
        chatBox.innerHTML += `<p><strong>Bot:</strong> ${data.response}</p>`;
        document.getElementById("user-input").value = "";
        userInp.disabled = false;
        userInp.placeholder = "Type a message...";
        sendButton.disabled = false;
    });
}

function cancel() {
    fetch("/cancel", {
        method: "POST",
        body: JSON.stringify({employee_id: emp_id}),
        headers: { "Content-Type": "application/json" }
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById(data.context).remove();
        chatBox.innerHTML += `<p><strong>Bot:</strong> ${data.response}</p>`;
        document.getElementById("user-input").value = "";
        userInp.disabled = false;
        userInp.placeholder = "Type a message...";
        sendButton.disabled = false;
    });
}

window.addEventListener('beforeunload', function() {
    fetch("/unload", {
        method: "POST",
        body: JSON.stringify({}),
        headers: { "Content-Type": "application/json" }
    })
    .then(response => response.json())
    .then(data => {
        userInp.disabled = false;
        userInp.placeholder = "Type a message...";
        sendButton.disabled = false;
    });
});
