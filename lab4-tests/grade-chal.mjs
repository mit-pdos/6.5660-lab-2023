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
    var answerPath = studentDir + "/answer-chal.html";
    var screenshotPath = studentDir + "/lab4-tests/answer-chal.png";
    if (!fs.isFile(answerPath)) {
        grading.failed("No answer-chal.html");
        phantom.exit();
        return;
    }

    // Allow both http://localhost:8080/zoobar/index.cgi/login and
    // the redirect from http://localhost:8080/zoobar/index.cgi/
    var allowedUrls = {};
    allowedUrls["http://localhost:8080/zoobar/index.cgi/login?nexturl=http://localhost:8080/zoobar/index.cgi/"] = 1;
    allowedUrls["http://localhost:8080/zoobar/index.cgi/login"] = 1;

    grading.registerTimeout();

    // Initialize the world.
    var graderPassword = grading.randomPassword();
    await grading.initUsers(async function(auth) {
        // Log out.
        await phantom.clearCookies();

        console.log("Loading attacker page");
        var page = await webpage.create();
        page.onLoadFinished = async function(status) {
            console.log(page.url);
            if (page.url in allowedUrls) {
                console.log("Redirected to login page.");
                page.onLoadFinished = null;

                // Smile!
                await grading.derandomize(page);
                await page.render(screenshotPath);
                await grading.compare(screenshotPath, async function() {
                    console.log("Entering grader/" + graderPassword + " into form.");
                    await grading.submitLoginForm(page, "grader", graderPassword, async function() {
                        if (!await grading.check_log(graderPassword)) {
                            grading.failed("No password in log");
                            phantom.exit();
                        }

                        // Just check if we got a cookie.
                        if (await grading.getCookie("localhost", "PyZoobarLogin")) {
                            await grading.passed("User logged in");
                        } else {
                            await grading.failed("User not logged in");
                        }
                        
                        await page.close();
                        phantom.exit();
                    });
                });
            } else if (/^http:\/\/localhost:8080/.test(page.url)) {
                grading.failed("Target page has unexpected URL");
                console.log("   " + page.url);
                page.onLoadFinished = null;
                await page.close();
                phantom.exit();
            }
        };
       
        await page.open(`file://${process.cwd()}/${answerPath}`);
    }, graderPassword);
}

await main.apply(null, system.args.slice(1));
