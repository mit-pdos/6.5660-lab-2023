import * as grading from "./grading.mjs";
var fs = grading.fs;
var webpage = grading.webpage;
var system = grading.system;
var phantom = grading.phantom;

var NUM_ITERATIONS = 3;

async function testProfile(attackerCookies, studentDir, num, prevUser) {
    if (num > NUM_ITERATIONS) {
        phantom.exit();
        return;
    }
    var user = "grader" + num;
    await grading.zoobarRegister(user, "password" + num, async function() {
        var userCookies = (await phantom.cookies).slice(0);
        console.log("Viewing " + prevUser + " profile");
        var tempPage = await webpage.create();
        // visit transfer first as students will visit it, and it's unfair
        // to not count ref as the same just because of visited link color
        await grading.openOrDie(tempPage, grading.zoobarBase + 'transfer', async function () {
            var url = grading.zoobarBase + "users?user=" + encodeURIComponent(prevUser);
            await tempPage.close();
            var page = await webpage.create(); // new page, close temp page
            await grading.openOrDie(page, url, async function() {
                // Wait two seconds for the page to settle, profile propogated, etc.
                await new Promise(r => setTimeout(r, 2000));
                // Say cheese! num-1 because we are viewing the
                // previous profile.
                await grading.derandomize(page);
                const path = studentDir + "/lab4-tests/answer-10_" + (num - 1) + ".png";
                await page.render(path);
                await grading.compare(path, async function() {
                    // await page.close();

                        // Check that zoobars were stolen.
                        await grading.getZoobars(async function(number) {
                            if (number != 9) {
                                grading.failed("" + user + " has " + number + " zoobars");
                            } else {
                                grading.passed("" + user + " zoobars");
                            }

                            // Check that the attacker now has 1 more.
                            // await phantom.setCookies(auth.attackerCookies);
                            await grading.getZoobars(async function(number) {
                                if (number != 10 + num) {
                                    grading.failed("attacker has " + number + " zoobars");
                                } else {
                                    grading.passed("attacker zoobars");
                                }
                                // FINALLY. Go loop again.
                                await testProfile(attackerCookies, studentDir, num + 1, user);
                            },
                            attackerCookies);
                        },
                        userCookies);
                });
            });
        });
    });
}

async function main(studentDir) {
    if (studentDir === undefined) {
        console.log("USAGE: node " + system.args[0] + " student_dir/");
        phantom.exit();
        return;
    }
    var answerPath = studentDir + "/answer-10.txt";
    if (!fs.isFile(answerPath)) {
        grading.failed("No answer-10.txt");
        phantom.exit();
        return;
    }

    grading.registerTimeout(60);

    // Initialize just the attacker account this time.
    await grading.zoobarRegister("attacker", "attackerpassword", async function() {
        const cookies = await phantom.cookies;
        var attackerCookies = cookies.slice(0);
        console.log("Installing attacker profile");
        await grading.setProfile(fs.read(answerPath), async function() {
            await testProfile(attackerCookies, studentDir, 1, "attacker");
        });
    });
}

await main.apply(null, system.args.slice(1));
