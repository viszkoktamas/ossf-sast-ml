const fs = require("fs");
const acornLoose = require("acorn-loose");
const recast = require("recast");
const path = require('path');
const {promisify} = require('util');
const exec = promisify(require('child_process').exec)

function findAllFunctions(root, functionsList) {
    if (!root)
        return;
    if (!!root.forEach) {
        root.forEach(el => {
            findAllFunctions(el, functionsList);
        })
    }
    if (!root.type)
        return;
    if (!!root.type && root.type.includes("Function")) {
        let functionBody = recast.print(root).code;
        functionsList.push({functionBody, startLine: root.loc.start.line, endLine: root.loc.end.line, nodeType: root.type});
    }
    (Object.keys(root) || []).forEach(k => {
        findAllFunctions(root[k], functionsList)
    })
}

function extractFunctionsFromFile(filePath) {
    let file = fs.readFileSync(path.resolve(filePath), "utf8");
    let functionArg = acornLoose.parse(file, {locations: true});
    let functions = [];
    findAllFunctions(functionArg, functions);
    return functions;
}

function isCodeDir(dirName) {
    return !['node_modules', '.idea', 'test', 'tests', 'build', 'dist', 'assets', 'docs', 'venv'].includes(dirName);
}

function isCodeFile(fileName) {
    let parsedFileName = path.parse(fileName);
    return ['.js', '.ts', '.mjs', '.mts'].includes(parsedFileName.ext) && !['package'].includes(parsedFileName.name);
}

function listFiles(filePath) {
    let pathInfo = fs.lstatSync(filePath, {throwIfNoEntry: false});
    if (pathInfo?.isFile()) {
        return [filePath];
    } else if (!pathInfo?.isDirectory()) {
        return [];
    }
    let files = [];
    fs.readdirSync(filePath).forEach((fileName) => {
        let file = filePath + path.sep + fileName;
        let fileInfo = fs.lstatSync(file);
        if (fileInfo.isDirectory() && isCodeDir(fileName)) files.push(...listFiles(file));
        else if (fileInfo.isFile() && isCodeFile(fileName)) files.push(file);
    });
    return files;
}

function extractFunctionsFromPaths(paths, outFile) {
    if (!outFile) {
        outFile = 'result.json';
    }
    let data = [];
    paths.forEach((path) => {
        listFiles(path).forEach((filePath) => {
            data.push({
                filePath,
                messages: extractFunctionsFromFile(filePath)
            });
            data[filePath] = extractFunctionsFromFile(filePath);
        });
    });
    fs.writeFile(outFile, JSON.stringify(data), 'utf8', (err) => {
        if (err) console.log("Something went wrong: ", err);
    });
    return outFile;
}

const execute = async (paths, output) => {
    console.log("Execute: (paths=", paths, ', output="'+ output+ '")')
    let outFile = extractFunctionsFromPaths(paths, output);
    try {
        let cmdRes = await exec(`inference ${outFile}`);
        let res = cmdRes.stdout.trim();
        console.log(res);
    } catch (e) {
        throw new Error("Could not run inference for " + outFile + ", error: " + e);
    }
    return outFile;
}


module.exports = {execute};
