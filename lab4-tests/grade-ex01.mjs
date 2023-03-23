import * as grading from "./grading.mjs";
var fs = grading.fs;
var webpage = grading.webpage;
var system = grading.system;
var phantom = grading.phantom;

async function main(studentDir) {
    if (studentDir === undefined) {
        console.log("USAGE: node " + system.args[0] + " student_dir/");
        phantom.exit();
        return;
    }
    var answerPath = studentDir + "/answer-1.js";

    if (!fs.isFile(answerPath)) {
        grading.failed("No answer-1.js");
        phantom.exit();
        return;
    }

    var url = "http://localhost:8080/zoobar/index.cgi/users";

    grading.registerTimeout();

    // First login.
    await grading.initUsers(async function(auth) {
        await phantom.setCookies(auth.graderCookies);

        var correctCookie = await grading.getCookie("localhost", "PyZoobarLogin");

        console.log("Expecting cookie: " + correctCookie);

        // Now make a new page and open the attacker's URL.
        var page = await webpage.create();

        var finished = false;

        page.onAlert = async function(dialog) {
            const content = dialog.message();
            const msg = "alert contains: " + correctCookie;
            if (content.indexOf(correctCookie) > -1) {
              grading.passed(msg);
            } else {
              grading.failed(msg);
            }
            finished = true;
            await dialog.dismiss();
        };

        await grading.openOrDie(page, url, async function() {

            //this injects the javascript in the file.
            if (await page.injectJs(answerPath) == false) {
                grading.failed("File contains invalid javascript")
                finished = true
            }
            // Wait 2s for any JS to settle and take a picture.
            setTimeout(async function () {
                await grading.derandomize(page);

                //make sure we show the fail message if no alert was triggered
                if (finished == false) {
                    grading.failed("Timeout, no alert was triggered")
                }
                phantom.exit();
            }, 1000);
        });
    });
}

await main.apply(null, system.args.slice(1));