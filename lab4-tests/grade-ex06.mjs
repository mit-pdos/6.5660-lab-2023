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
    var answerPath = studentDir + "/answer-6.html";
    if (!fs.isFile(answerPath)) {
        grading.failed("No answer-6.html");
        phantom.exit();
        return;
    }

    grading.registerTimeout();

    // Initialize the world.
    var graderPassword = grading.randomPassword();
    await grading.initUsers(async function(auth) {
        await testLoggedOut(answerPath, graderPassword);
    }, graderPassword);
}

async function testLoggedOut(answerPath, graderPassword) {
    await phantom.clearCookies();

    var page = await webpage.create();
    
    await grading.openOrDie(page, `file://${process.cwd()}/${answerPath}`, async function() {
        // Wait 100ms for it to settle. Shouldn't need to, but meh.
        setTimeout(async function() {
            // Submit the form. This may break horribly if the student
            // didn't name things identically, but hopefully they
            // started from a copy of the real thing.
            console.log("Entering grader/" + graderPassword + " into form.");

            await grading.submitLoginForm(page, "grader", graderPassword, async function() {
                // Just check if we got a cookie.
                const cookie = await grading.getCookie("localhost", "PyZoobarLogin");
                console.log(cookie);
                if (cookie) {
                    grading.passed("User logged in");
                } else {
                    grading.failed("User not logged in");
                }
                
                await page.close();
                phantom.exit();
            });
        }, 100);
    });
}

await main.apply(null, system.args.slice(1));
