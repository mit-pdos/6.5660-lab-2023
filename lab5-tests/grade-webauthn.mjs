import * as grading from "./grading.mjs";
var fs = grading.fs;
var webpage = grading.webpage;
var system = grading.system;
var phantom = grading.phantom;

const zoobar_real = 'zoobar-localhost.csail.mit.edu';
const zoobar_fake = 'zoobar-localhost-other.csail.mit.edu';

async function saveCred(page) {
    const creds = await page.getCreds();
    if (creds.credentials.length != 1) {
        grading.failed("Expected 1 credential, found " + creds.credentials.length);
    }

    return creds.credentials[0];
}

async function main() {
    grading.registerTimeout(120);

    var grader1_cred = null;
    var grader2_cred = null;
    var opts = {};

    await grading.zoobarRegister(zoobar_real, "grader1", async function(page, ok) {
        if (ok) {
            grader1_cred = await saveCred(page);
            grading.passed("Registered grader1");
        } else {
            grading.failed("Registering grader1 failed");
            phantom.exit();
        }
    });

    grader1_cred.rpId = zoobar_real;
    await grading.zoobarLogin(zoobar_real, "grader1", grader1_cred, opts, async function(page, ok) {
        if (ok) {
            grading.passed("Logged in grader1");
        } else {
            grading.failed("Logging in as grader1 failed");
            phantom.exit();
        }
    });

    opts.overrideCredsGetChallenge = opts.credsGetChallenge;
    await grading.zoobarLogin(zoobar_real, "grader1", grader1_cred, opts, async function(page, ok) {
        if (ok) {
            grading.failed("Logged in grader1 with replayed challenge");
            phantom.exit();
        } else {
            grading.passed("Login with replayed challenge blocked");
        }
    });

    opts.overrideCredsGetChallenge = null;
    grader1_cred.rpId = zoobar_fake;
    await grading.zoobarLogin(zoobar_fake, "grader1", grader1_cred, opts, async function(page, ok) {
        if (ok) {
            grading.failed("Logged in as grader1 from wrong origin");
            phantom.exit();
        } else {
            grading.passed("Login from wrong origin blocked");
        }
    });

    await grading.zoobarRegister(zoobar_real, "grader2", async function(page, ok) {
        if (ok) {
            grader2_cred = await saveCred(page);
            grading.passed("Registered grader2");
        } else {
            grading.failed("Registering grader2 failed");
            phantom.exit();
        }
    });

    grader2_cred.rpId = zoobar_real;
    opts.credsGetCallback = async function() {
        opts.credsGetCallback = null;
        await grading.zoobarLogin(zoobar_real, "grader2", grader2_cred, opts, async function(page, ok) {
            if (ok) {
                grading.passed("Logged in grader2 concurrently (inner)");
            } else {
                grading.failed("Concurrent login as grader2 failed (inner)");
                phantom.exit();
            }
        });
    };

    await grading.zoobarLogin(zoobar_real, "grader2", grader2_cred, opts, async function(page, ok) {
        if (ok) {
            grading.passed("Logged in grader2 concurrently (outer)");
        } else {
            grading.failed("Concurrent login as grader2 failed (outer)");
            phantom.exit();
        }
    });

    opts.overrideCredsGetChallenge = [0];
    await grading.zoobarLogin(zoobar_real, "grader2", grader2_cred, opts, async function(page, ok) {
        if (ok) {
            grading.failed("Logged in grader2 with bogus challenge");
            phantom.exit();
        } else {
            grading.passed("Login as grader2 with bogus challenge blocked");
        }
    });

    opts.overrideCredsGetChallenge = opts.credsGetChallenge;
    grader1_cred.rpId = zoobar_real;
    await grading.zoobarLogin(zoobar_real, "grader1", grader1_cred, opts, async function(page, ok) {
        if (ok) {
            grading.failed("Logged in grader1 with challenge from grader2");
            phantom.exit();
        } else {
            grading.passed("Login as grader1 with mismatched challenge blocked");
        }
    });

    grader2_cred.privateKey = grader1_cred.privateKey;
    await grading.zoobarLogin(zoobar_real, "grader2", grader2_cred, opts, async function(page, ok) {
        if (ok) {
            grading.failed("Logged in as grader2 with wrong private key");
            phantom.exit();
        } else {
            grading.passed("Login with wrong private key blocked");
        }
    });

    await grading.zoobarRegister(zoobar_real, "grader1", async function(page, ok) {
        if (ok) {
            grading.failed("Registered twice as grader1");
            phantom.exit();
        } else {
            grading.passed("Duplicate registration for grader1 blocked");
        }
    });

    await grading.zoobarRegister(zoobar_fake, "grader3", async function(page, ok) {
        if (ok) {
            grading.failed("Registered from wrong origin");
            phantom.exit();
        } else {
            grading.passed("Registration from wrong origin blocked");
        }
    });

    phantom.exit();
}

await main();
