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

    try {
      await grading.zoobarRegister(zoobar_real, "grader1", async function(page, ok) {
          if (ok) {
              grader1_cred = await saveCred(page);
              grading.passed("EX1 Registered grader1");
          } else {
              grading.failed("EX1 Registering grader1 failed");
              phantom.exit();
          }
      });
    } catch (error) {
      grading.failed("EX1 ERROR: " + error.message);
    }

    try {
      grader1_cred.rpId = zoobar_real;
      await grading.zoobarLogin(zoobar_real, "grader1", grader1_cred, opts, async function(page, ok) {
          if (ok) {
              grading.passed("EX2 Logged in grader1");
          } else {
              grading.failed("EX2 Logging in as grader1 failed");
              phantom.exit();
          }
      });
    } catch (error) {
      grading.failed("EX2 ERROR: " + error.message);
    }

    try {
      opts.overrideCredsGetChallenge = opts.credsGetChallenge;
      await grading.zoobarLogin(zoobar_real, "grader1", grader1_cred, opts, async function(page, ok) {
          if (ok) {
              grading.failed("EX3 Logged in grader1 with replayed challenge");
              phantom.exit();
          } else {
              grading.passed("EX3 Login with replayed challenge blocked");
          }
      });
    } catch (error) {
      grading.failed("EX3 ERROR: " + error.message);
    }

    try {
      opts.overrideCredsGetChallenge = null;
      grader1_cred.rpId = zoobar_fake;
      await grading.zoobarLogin(zoobar_fake, "grader1", grader1_cred, opts, async function(page, ok) {
          if (ok) {
              grading.failed("EX4 Logged in as grader1 from wrong origin");
              phantom.exit();
          } else {
              grading.passed("EX4 Login from wrong origin blocked");
          }
      });
    } catch (error) {
      grading.failed("EX4 ERROR: " + error.message);
    }

    try {
      await grading.zoobarRegister(zoobar_real, "grader2", async function(page, ok) {
          if (ok) {
              grader2_cred = await saveCred(page);
              grading.passed("EX5-1 Registered grader2");
          } else {
              grading.failed("EX5-1 Registering grader2 failed");
              phantom.exit();
          }
      });

      grader2_cred.rpId = zoobar_real;
      opts.credsGetCallback = async function() {
          opts.credsGetCallback = null;
          await grading.zoobarLogin(zoobar_real, "grader2", grader2_cred, opts, async function(page, ok) {
              if (ok) {
                  grading.passed("EX5-2 Logged in grader2 concurrently (inner)");
              } else {
                  grading.failed("EX5-2 Concurrent login as grader2 failed (inner)");
                  phantom.exit();
              }
          });
      };

      await grading.zoobarLogin(zoobar_real, "grader2", grader2_cred, opts, async function(page, ok) {
          if (ok) {
              grading.passed("EX5-3 Logged in grader2 concurrently (outer)");
          } else {
              grading.failed("EX5-3 Concurrent login as grader2 failed (outer)");
              phantom.exit();
          }
      });
    } catch (error) {
      grading.failed("EX5 ERROR: " + error.message);
    }

    try {
      opts.overrideCredsGetChallenge = [0];
      await grading.zoobarLogin(zoobar_real, "grader2", grader2_cred, opts, async function(page, ok) {
          if (ok) {
              grading.failed("EX6 Logged in grader2 with bogus challenge");
              phantom.exit();
          } else {
              grading.passed("EX6 Login as grader2 with bogus challenge blocked");
          }
      }); 
    } catch (error) {
      grading.failed("EX6 Logged in as grader1 from wrong origin ERROR: " + error.message);
    }

    try {
      opts.overrideCredsGetChallenge = opts.credsGetChallenge;
      grader1_cred.rpId = zoobar_real;
      await grading.zoobarLogin(zoobar_real, "grader1", grader1_cred, opts, async function(page, ok) {
          if (ok) {
              grading.failed("EX7 Logged in grader1 with challenge from grader2");
              phantom.exit();
          } else {
              grading.passed("EX7 Login as grader1 with mismatched challenge blocked");
          }
      });
    } catch (error) {
      grading.failed("EX7 Logged in as grader1 from wrong origin ERROR: " + error.message);
    }

    try {
      grader2_cred.privateKey = grader1_cred.privateKey;
      await grading.zoobarLogin(zoobar_real, "grader2", grader2_cred, opts, async function(page, ok) {
          if (ok) {
              grading.failed("EX8 Logged in as grader2 with wrong private key");
              phantom.exit();
          } else {
              grading.passed("EX8 Login with wrong private key blocked");
          }
      });
    } catch (error) {
      grading.failed("EX8 ERROR: " + error.message);
    }

    try {
    await grading.zoobarRegister(zoobar_real, "grader1", async function(page, ok) {
        if (ok) {
            grading.failed("EX9 Registered twice as grader1");
            phantom.exit();
        } else {
            grading.passed("EX9 Duplicate registration for grader1 blocked");
        }
    });
    } catch (error) {
      grading.failed("EX9 ERROR: " + error.message);
    }

    try {
      await grading.zoobarRegister(zoobar_fake, "grader3", async function(page, ok) {
          if (ok) {
              grading.failed("EXA Registered from wrong origin");
              phantom.exit();
          } else {
              grading.passed("EXA Registration from wrong origin blocked");
          }
      });
    } catch (error) {
      grading.failed("EXA ERROR: " + error.message);
    }

    phantom.exit();
}

await main();
