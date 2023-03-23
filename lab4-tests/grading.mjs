import * as puppeteer from "puppeteer"
import * as npmfs from "fs";

export var phantom = await (async () => {
  const browser = await puppeteer.launch(
      {
        // headless: false, slowMo: 250,
        args: [ '--ignore-certificate-errors' ], defaultViewport: null}
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

export var fs = (() => {
  return {
    isFile: (path) => npmfs.existsSync(path),
    readFileSync: (path) => npmfs.readFileSync(path,'utf8'),
    read: (path, options=null) => {
      let encoding = 'utf8';
      if (options && options.mode) {
        encoding = options.mode;
      }
      return npmfs.readFileSync(path,encoding);
    },
    exists: (path) => npmfs.existsSync(path),
    remove: (path) => npmfs.rmSync(path),
    copy: (src, dest) => npmfs.copyFileSync(src, dest),
  };
})();

export var system = (() => {
  return {
    args: process.argv.slice(1),
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
        injectJs: async (file) => {
          const script = fs.readFileSync(file,'utf8');
          try {
            await page.evaluate((script) => eval(script), script);
          } catch (e) {
            return false;
          }
          return true;
        },
        render: async (path) => {
          await page.screenshot({path, captureBeyondViewport: false});
        },
        close: async () => await page.close(),
        target: () => page.target(),
        click: async (selector, options) => await page.click(selector, options),
        setCookies: async (c) => await page.setCookie(...c),
        waitForNavigation: async () => await page.waitForNavigation(),
        exposeFunction: async (name, fn) => await page.exposeFunction(name, fn),
      };
      return phantom.page;
    },
  };
})();

// END NEW EXPORTS

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

export var zoobarBase = "http://localhost:8080/zoobar/index.cgi/";

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

// Siiigh.
export async function derandomize(page) {
    await page.evaluate(function() {
        NodeList.prototype.forEach = Array.prototype.forEach;  // asdfsdf
        document.querySelectorAll("h1 > a").forEach(function(a) {
            if (/^Zoobar Foundation for /.test(a.textContent))
                a.textContent = "Zoobar Foundation for <snip> <snip>";
        });
        document.querySelectorAll("h2").forEach(function(h2) {
            if (/^Supporting the /.test(h2.textContent))
                h2.textContent = "Supporting the <snip> <snip> of the <snip>";
        });
    });
}

async function zoobarLoginHelper(submit, user, pass, cb) {
    await phantom.clearCookies();
    var page = await webpage.create();
    await openOrDie(page, zoobarBase + "login", async function() {
        await page.evaluate(function(submit, user, pass) {
            var f = document.forms["loginform"];
            f.login_username.value = user;
            f.login_password.value = pass;
            // f[submit].click();
        }, submit, user, pass);
        await Promise.all([
          page.waitForNavigation(),
          page.click(`input[name=${submit}]`, {waitUntil: 'domcontentloaded'}),
        ]);
        
        if (page.url != zoobarBase) {
            console.log("Login failed");
            await page.close();
            phantom.exit();
        } else {
            await cb();
            await page.close(); // close after cb, since cb needs cookies
        }
    });
}

export async function zoobarLogin(user, pass, cb) {
    console.log("Logging in as " + user + ", " + pass)
    await zoobarLoginHelper("submit_login", user, pass, cb);
}

export async function zoobarRegister(user, pass, cb) {
    console.log("Registering as " + user + ", " + pass)
    await zoobarLoginHelper("submit_registration", user, pass, cb);
}

export async function initUsers(cb, graderPassword) {
    if (graderPassword === undefined)
        graderPassword = "graderpassword";
    await zoobarRegister("grader", graderPassword, async function() {
        var graderCookies = (await phantom.cookies).slice(0);
        await phantom.clearCookies();
        await zoobarRegister("attacker", "attackerpassword", async function() {
            var attackerCookies = (await phantom.cookies).slice(0);
            await phantom.clearCookies();
            await cb({
                graderCookies: graderCookies,
                attackerCookies: attackerCookies
            });
        });
    });
}

export async function getZoobars(cb, cookies = null) {
    // You can't do an XHR manually. Lame. Pick a page that cannot
    // possibly have XSS problems and do an XHR from there.
    var page = await webpage.create();
    if (cookies) {
      await page.setCookies(cookies);
    }
    await openOrDie(page, zoobarBase + "transfer", async function() {
        // page.onCallback = async function(data) {
            // page.onCallback = null;
            // await cb(data);
        // };
        await page.exposeFunction('callPhantom', async data => {
          await cb(data);
          await page.close();
        });
        await page.evaluate(function() {
            var xhr = new XMLHttpRequest();
            xhr.open("GET", "zoobarjs", true);
            xhr.responseType = "text";
            xhr.onload = async function(e) {
                var lines = xhr.responseText.split("\n");
                for (var i = 0; i < lines.length; i++) {
                    var m = /^var myZoobars = (\d+);/.exec(lines[i]);
                    if (m && m[1]) {
                        await window.callPhantom(Number(m[1]));
                        break;
                    }
                }
            };
            xhr.send();
        });
    });
}

export async function setProfile(profile, cb, cookies = null) {
    var page = await webpage.create();
    if (cookies) {
      await page.setCookies(cookies);
    }
    await openOrDie(page, zoobarBase, async function() {
        await Promise.all([
            page.waitForNavigation(), // The promise resolves after profile is updated
            page.evaluate(function(profile) {
                var f = document.forms["profileform"];
                f.profile_update.value = profile;
                f.profile_submit.click();
            }, profile),
        ]);
        await page.close();
        await cb();
    });
}

export async function getProfile(cb) {
    var page = await webpage.create();
    openOrDie(page, zoobarBase, async function() {
        var profile = await page.evaluate(function() {
            var f = document.forms["profileform"];
            return f.profile_update.value;
        });
        await cb(profile);
        await page.close();
    });
}

export function findSubmitButton(f) {
    // The official solution does dumb things with the submit
    // button. I'm not sure anyone else's is quite as weird, but
    // just in case, find the first visible login button.
    for (var i = 0; i < f.length; i++) {
        var style = getComputedStyle(f[i]);
        if (style.display == "none" || style.visibility == "hidden")
            continue;
        if (f[i].type != "button" && f[i].type != "submit")
            continue;
        if (f[i].value != "Log in")
            continue;
        return f[i];
    }
    var buttons = document.getElementsByTagName("button");
    for (var i = 0; i < buttons.length; i++) {
        var style = getComputedStyle(buttons[i]);
        if (style.display == "none" || style.visibility == "hidden")
            continue;
        if (buttons[i].textContent != "Log in")
            continue;
        return buttons[i];
    }
    return null;
}

export async function submitLoginForm(page, user, pass, cb) {
    var oldUrl = page.url;
    page.onLoadFinished = async function(status) {
        // PhantomJS is dumb and runs this even on iframe loads. So
        // check that the top-level URL changed.
        if (oldUrl == page.url) return;
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
    }, user, pass, findSubmitButton.toString());
}

export function randomPassword() {
    var s = "";
    var a = "A".charCodeAt(0);
    for (var i = 0; i < 12; i++) {
        s += String.fromCharCode(a + Math.floor(Math.random() * 26));
    }
    return s;
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

export async function check_log(expecting) {
    const url = 'https://css.csail.mit.edu/6.5660/2023/labs/log.php';
    const req = await fetch(url);
    const body = await req.text();
    if (body.includes(expecting)) {
        return true;
    } else {
        console.log("[ \u001b[31mERROR\u001b[39m]: did not find '\u001b[33m" + expecting + "\u001b[39m' at " + url);
        return false;
    }
}

async function decode(path, ondone) {
    var page = await webpage.create();
    page.onAlert = async function(dialog) {
        await dialog.dismiss(); // dismiss alert to allow new js evaluation
        ondone(await page.evaluate(function() {
          return window.imgdata;}));
        await page.close();
    };

    page.content = '<html><body></body></html>';
    await page.evaluate(function(imgdata){
        var canvas = document.createElement("canvas");
        var ctx = canvas.getContext("2d");
        var image = new Image();
        image.onload = function() {
            canvas.width = image.width;
            canvas.height = image.height;
            ctx.drawImage(image, 0, 0);
            window.imgdata = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
            alert(window.imgdata.length);
        };
        image.src = "data:image/png;base64," + imgdata;
    }, fs.read(path, {mode: 'base64'}));
}

export async function compare(path, done) {
    var refpath = path.replace('.png', '.ref.png');

    var pixels = [];
    function ondone(pxs) {
        const pxsLength = Object.keys(pxs).length;
        var cp = []
        // each image is a 1d array (in rgba order) of decoded pixel data
        for (var i = 0; i < pxsLength; i+=4) {
            if (pxs[i] == 204 && pxs[i+1] == 204 && pxs[i+2] == 204 && pxs[i+3] == 255) {
                // remove background colored pixels
                continue
            }
            cp.push(pxs[i], pxs[i+1], pxs[i+2], pxs[i+3]);
        }
        pixels.push(cp);

        if (pixels.length == 1) {
            return;
        }

        if (pixels[0].length != pixels[1].length) {
            failed(path + " did not match reference image (different size)");
            done();
            return
        }
        for (i = 0; i < pixels[0].length; i++) {
            if (pixels[0][i] != pixels[1][i]) {
                failed(path + " did not match reference image (pixel mismatch; " + pixels[0][i] + " != " + pixels[1][i] + ")");
                console.log('yours:', pixels[0][i], pixels[0][i+1], pixels[0][i+2], pixels[0][i+3]);
                console.log('ours:', pixels[1][i], pixels[1][i+1], pixels[1][i+2], pixels[1][i+3]);
                done();
                return
            }
        }
        passed(path + " matched reference image (" + pixels[0].length + " non-background pixels)");
        done();
    }
    await decode(path, ondone);
    await decode(refpath, ondone);
}
