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
    var answerPath = studentDir + "/answer-7.html";
    if (!fs.isFile(answerPath)) {
        grading.failed("No answer-7.html");
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

            await submitLoginFromClick(page, "grader", graderPassword, async function() {
                // Just check if we got a cookie.
                if (await grading.getCookie("localhost", "PyZoobarLogin")) {
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

async function submitLoginFromClick(page, user, pass, cb) {
    var oldUrl = page.url;
    var alerted = false;
    page.onAlert = async function(dialog) {
        const content = dialog.message();
        if (content.indexOf(pass) > -1) {
            grading.passed("alert contains user password: " + pass);
        } else {
            grading.failed("alert doesn't contain user password: " + pass + ' not in ' + content);
        }
        alerted = true;
        
        await dialog.dismiss();
    };

    page.onLoadFinished = async function(status) {
        // PhantomJS is dumb and runs this even on iframe loads. So
        // check that the top-level URL changed.
        if (oldUrl == page.url) return;
        if (!alerted) {
            grading.failed("no alert shown");
        }
        page.onLoadFinished = null;
        await cb();
    };
    await page.evaluate(async function(user, pass, fnStr) {
        var f = document.forms["loginform"];
        f.login_username.value = user;
        f.login_password.value = pass;

        var findButton = new Function(`return ${fnStr}.apply(null, arguments)`);
        var button = findButton(f);
        if (!button)
            throw "Could not find login button";
        button.click();
    }, user, pass, grading.findSubmitButton.toString());
}

await main.apply(null, system.args.slice(1));
