import * as grading from "./grading.mjs";
var fs = grading.fs;
var webpage = grading.webpage;
var system = grading.system;
var phantom = grading.phantom;

const ex4msg = "Scanning for viruses...";
var NUM_ITERATIONS = 3;

async function make_refimg_ex4(num, prevUser) {
    if (num > NUM_ITERATIONS) {
        phantom.exit();
        return;
    }
    var user = "grader" + num;
    await grading.zoobarRegister(user, "password" + num, async function () {
        await grading.setProfile(ex4msg, async function () {
            var page = await webpage.create();
            // visit transfer first as students will visit it, and it's unfair
            // to not count ref as the same just because of visited link color
            await grading.openOrDie(page, grading.zoobarBase + 'transfer', async function () {
                var url = grading.zoobarBase + "users?user=" + encodeURIComponent(prevUser);
                await grading.openOrDie(page, url, async function () {
                    // Wait for the zoobar counter to settle
                    await new Promise(r => setTimeout(r, 2000));
                    await grading.derandomize(page);
                    await page.render("lab4-tests/answer-10_" + (num - 1) + ".ref.png");
                    await page.close();

                    await make_refimg_ex4(num + 1, user);
                });
            });
        });
    });
}

async function main() {
    await grading.initUsers(async function(auth) {
        // answer-1.png: as grader, view a blank users page.
        var page = await webpage.create();
        await page.setCookies(auth.graderCookies);
        await grading.openOrDie(page, grading.zoobarBase + "users", async function() {
            await grading.derandomize(page);
            await page.render("lab4-tests/answer-5.ref.png");
            await page.close();
            
            // answer-chal.png: view the login page.
            await phantom.clearCookies();
            let newPage = await webpage.create();
            await grading.openOrDie(newPage, grading.zoobarBase + "login", async function() {
                await grading.derandomize(newPage);
                await newPage.render("lab4-tests/answer-chal.ref.png");
                await newPage.close();

                // await phantom.setCookies(auth.attackerCookies);
                await grading.setProfile(ex4msg, async function () {
                    await make_refimg_ex4(1, "attacker");
                },
                auth.attackerCookies);
            });
            phantom.exit();
            return;
        });
    });
}

await main.apply(null, system.args.slice(1));
