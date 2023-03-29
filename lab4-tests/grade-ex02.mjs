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
    var answerPath = studentDir + "/answer-2.js";

    if (!fs.isFile(answerPath)) {
        grading.failed("No answer-2.js");
        phantom.exit();
        return;
    }

    var url = "http://localhost:8080/zoobar/index.cgi/users";

    grading.registerTimeout();

    // First login.
    await grading.initUsers(async function(auth) {
        await phantom.setCookies(auth.graderCookies);

        // Now make a new page and open the attacker's URL.
        var page = await webpage.create();

        await grading.openOrDie(page, url, async function() {

            //this injects the javascript in the file.
            if (await page.injectJs(answerPath) == false) {
                grading.failed("File contains invalid javascript")
                // finished = true
            }
            // Wait 1s for any JS to settle and take a picture.
            setTimeout(async function () {
                await grading.derandomize(page);

                // Print out the cookie we expect.
                if (await grading.check_log(await grading.getCookie("localhost", "PyZoobarLogin"))) {
                    grading.passed("Found cookie in log");
                } else {
                    grading.failed("No cookie in log");
                }

                phantom.exit();
            }, 2000);
        });
    });
}

await main.apply(null, system.args.slice(1));
