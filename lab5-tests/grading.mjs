import * as puppeteer from "puppeteer";
import fetch from "node-fetch";

export var phantom = await (async () => {
  const browser = await puppeteer.launch(
      {
        // headless: false, slowMo: 250,
        args: [ '--auto-open-devtools-for-tabs' ],
        defaultViewport: null,
      }
  );
  return {
    browser,
    exit: process.exit,
    get cookies() {
      return (async () => {
        const pages = await browser.pages();
        const page = pages[pages.length-1];
        const cookies = await page.cookies();
        return cookies;
      })();
    },
    setCookies: async (c) => {
      const pages = await browser.pages();
      const page = pages[pages.length-1];
      await page.setCookie(...c);
    },
    clearCookies: async () => {
      const pages = await browser.pages();
      const page = pages[pages.length-1];
      const client = await page.target().createCDPSession();
      await client.send('Network.clearBrowserCookies');
    }
  };
})();

const failureCallback = function(e) {
    var msg = e.message;
    var msgStack = ['\u001b[31mPHANTOM ERROR:\u001b[39m ' + msg, e.stack];
    console.error(msgStack.join('\n'));
    phantom.exit();
};

export var webpage = (() => {
  return {
    create: async () => {
      const page = await phantom.browser.newPage();

      // See https://chromedevtools.github.io/devtools-protocol/tot/WebAuthn/
      const cdp_client = await page.target().createCDPSession();
      await cdp_client.send('WebAuthn.enable', { enableUI: false });

      const authOptions = {
        protocol: "ctap2",
        ctap2Version: "ctap2_1",
        transport: "usb",
        hasResidentKey: false,
        hasUserVerification: false,
        hasLargeBlob: false,
        hasCredBlob: false,
        hasMinPinLength: false,
        hasPrf: false,
        hasUvm: false,
        automaticPresenceSimulation: true,
        isUserVerified: false,
        isUserConsenting: false
      };
      const add_res = await cdp_client.send('WebAuthn.addVirtualAuthenticator', {options: authOptions});
      const authenticator_id = add_res.authenticatorId;
      // console.log("Added virtual authenticator", authenticator_id);

      phantom.page = {
        // commonLoadHandlers
        get url() {return page.url()},

        // other stuff
        set onLoadFinished(callback) {
          page.off('load', this.onLoadHandler);
          this.onLoadHandler = callback;
          page.on('load', callback);
        },
        set onAlert(callback) {
          page.off('dialog', this.onAlertHandler);
          this.onAlertHandler = callback;
          page.on('dialog', callback);
        },
        
        // functions
        open: async (url, callback) => {
          const res = await page.goto(url, {waitUntil: 'domcontentloaded'});
          return callback && (await callback(res.status() == "200" ? "success" : "failure"));
        },
        evaluate: async (...args) => await page.evaluate(...args),
        render: async (path) => {
          await page.screenshot({path, captureBeyondViewport: false});
        },
        close: async () => await page.close(),
        target: () => page.target(),
        click: async (selector, options) => await page.click(selector, options),
        setCookies: async (c) => await page.setCookie(...c),
        waitForNavigation: async () => await page.waitForNavigation(),
        exposeFunction: async (name, fn) => await page.exposeFunction(name, fn),

        getCreds: async () => await cdp_client.send('WebAuthn.getCredentials', {authenticatorId: authenticator_id}),
        addCred: async (c) => await cdp_client.send('WebAuthn.addCredential', {authenticatorId: authenticator_id, credential: c}),
      };
      return phantom.page;
    },
  };
})();

phantom.onError = function(msg, trace) {
    var msgStack = ['\u001b[31mPHANTOM ERROR:\u001b[39m ' + msg];
    if (trace) {
        msgStack.push('TRACE:');
        trace.forEach(function(t) {
            msgStack.push(' -> ' + (t.file || t.sourceURL) + ': ' + t.line + (t.function ? ' (in function ' + t.function + ')' : ''));
        });
    }
    console.error(msgStack.join('\n'));
};

export async function getCookie(domain, name) {
    var cookies = (await phantom.cookies).filter(function(cookie) {
        return cookie.name == name &&
            (cookie.domain == domain || cookie.domain == "." + domain);
    });
    if (cookies.length > 0)
        return cookies[0].value;
    return null;
}

export async function openOrDie(page, url, cb) {
    await page.open(url, async function(status) {
        if (status != "success") {
            console.log("Loading '" + url + "' failed");
            await page.close();
            phantom.exit();
            return;
        }
        await cb();
    });
}

async function zoobarLoginHelper(origin, submit, user, cred, loginOpts, cb) {
    const base = "https://" + origin + ":8443/zoobar/index.cgi/";
    await phantom.clearCookies();
    var page = await webpage.create();
    await openOrDie(page, base + "login", async function() {
        if (cred) {
            await page.addCred(cred);
        }

        await page.exposeFunction('credsGetChallenge', async chal => {
            loginOpts.credsGetChallenge = chal;

            if (loginOpts.credsGetCallback) {
                await loginOpts.credsGetCallback();
            }
        });

        await page.evaluate(function(user, overrideCredsGetChallenge) {
            // Override navigator.credentials.get for grading purposes.
            var creds_get = navigator.credentials.get;
            navigator.credentials.get = async function (options) {
                if (options && options.publicKey) {
                    await window.credsGetChallenge(Array.from(options.publicKey.challenge));
                }
                if (overrideCredsGetChallenge && options && options.publicKey) {
                    options.publicKey.challenge = Uint8Array.from(overrideCredsGetChallenge, c => c);
                }
                const res = await creds_get.call(navigator.credentials, options);
                return res;
            };

            var f = document.forms["loginform"];
            f.login_username.value = user;
        }, user, loginOpts.overrideCredsGetChallenge);

        await Promise.all([
            page.waitForNavigation(),
            page.click(`input[name=${submit}]`, {waitUntil: 'domcontentloaded'}),
        ]);

        if (page.url != base) {
            console.log("Login failed");
            await cb(page, false);
            await page.close();
        } else {
            await cb(page, true);
            await page.close(); // close after cb, since cb needs cookies
        }
    });
}

export async function zoobarLogin(origin, user, cred, opts, cb) {
    console.log("Logging in as " + user)
    await zoobarLoginHelper(origin, "submit_login", user, cred, opts, cb);
}

export async function zoobarRegister(origin, user, cb) {
    console.log("Registering as " + user)
    await zoobarLoginHelper(origin, "submit_registration", user, null, {}, cb);
}

export function registerTimeout(seconds) {
    if (!seconds)
        seconds = 30;
    setTimeout(function() {
        console.log("[ \u001b[31mFAIL\u001b[39m ]: the grading script timed out")
        phantom.exit();
    }, seconds * 1000);
}

export function failed(msg) {
    console.log("[ \u001b[31mFAIL\u001b[39m ]: " + msg)
}

export function passed(msg) {
    console.log("[ \u001b[32mPASS\u001b[39m ]: " + msg)
}
