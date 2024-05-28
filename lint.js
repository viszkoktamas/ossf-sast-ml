const fs = require("fs");
const acornLoose = require("acorn-loose");
const recast = require("recast");
const path = require('path');
const {promisify} = require('util');
const exec = promisify(require('child_process').exec)
const {globSync} = require('glob');

function findAllFunctions(root, functionsList) {
    if (!root) return;
    if (!!root.forEach) {
        root.forEach((el) => {
            findAllFunctions(el, functionsList);
        })
    }
    if (!root.type) return;
    if (!!root.type && root.type.includes("Function")) {
        try {
            let functionBody = recast.print(root).code;
            functionsList.push({
                functionBody,
                startLine: root.loc.start.line,
                endLine: root.loc.end.line,
                nodeType: root.type
            });
        } catch (e) {
            console.error("Error while extracting function: ", e);
        }
    }
    (Object.keys(root) || []).forEach(k => {
        findAllFunctions(root[k], functionsList)
    })
}

function extractFunctionsFromFile(filePath) {
    let file = fs.readFileSync(path.resolve(filePath), "utf8");
    let functionArg = acornLoose.parse(file, {ecmaVersion: "latest", locations: true});
    let functions = [];
    findAllFunctions(functionArg, functions);
    return functions;
}

function getMyIgnorePatterns() {
    return ['**/node_modules/**', '**/java/**', '**/static/**', '**/spec/**', '**/build/**', '**/docs/**', '**/*asset*/**', '**/min/**', '**/dist/**', '**/*demo*/**', '**/*sample*/**', '**/*test*/**', '**/*.min.js', '**/demo.*', '**/*test*.*', '**/*jquery*.*'];
}

const getIgnorableFilePatternsFromProject = (inputPath) => ['.eslintignore', '.npmignore', '.gitignore', '.dockerignore']
    .flatMap((fileName) => {
    let ignoreFile = inputPath + path.sep + fileName;
    // @ts-ignore
    if (!!fs.lstatSync(ignoreFile, {throwIfNoEntry: false})?.isFile()) {
        const fileContent = fs.readFileSync(ignoreFile, 'utf-8');
        return fileContent.split(/\r?\n/);
    }
    return [];
});


function getProjectFiles(inputPath, ignoreFiles) {
    return globSync('**/*.{js,ts,mjs,mts}', {
        ignore: ignoreFiles,
        cwd: inputPath
    }).map((fp) => inputPath + path.sep + fp);
}

function extractFunctionsFromFilePath(inputPath) {
    return [{
        filePath: inputPath,
        messages: extractFunctionsFromFile(inputPath)
    }];
}

function extractFunctionsFromDirectoryPath(inputPath) {
    let ignoreFiles = Array.from(new Set([...getMyIgnorePatterns(), ...getIgnorableFilePatternsFromProject(inputPath)]));
    let filesList = getProjectFiles(inputPath, ignoreFiles);
    return filesList
        .map((filePath) => ({
            filePath: filePath,
            messages: extractFunctionsFromFile(filePath)
        }))
        .filter((e) => e.messages.length > 0);
}

function executePath(path) {
    // @ts-ignore
    let lstat = fs.lstatSync(path, {throwIfNoEntry: false});
    if (!!lstat?.isDirectory()) {
        return extractFunctionsFromDirectoryPath(path);
    } else if (!!lstat?.isFile()) {
        return extractFunctionsFromFilePath(path);
    }
    return [];
}

const execute = async (paths, outFile) => {
    if (!outFile) {
        outFile = 'result.json';
    }
    console.log('output="' + outFile + '"');
    let data = [];
    for (let path of paths) {
        console.log("Execute: (path=", path, ', output="' + outFile + '")');
        data.push(...executePath(path));
    }
    fs.writeFileSync(outFile, JSON.stringify(data, null, 2), 'utf8');
    try {
        let inferencePath = path.join(__dirname, "inference");
        let modelPath = path.join(inferencePath, "models");
        let cmdRes = await exec(`${inferencePath}.sh ${outFile} ${modelPath}`);
        let res = cmdRes.stdout.trim();
        console.log(res);
    } catch (e) {
        fs.writeFileSync(outFile, "Could not run inference for [" + paths.join(', ') + "], outFile: " + outFile + ", error: " + e, 'utf8');
        throw new Error("Could not run inference for " + outFile + ", error: " + e);
    }
}

module.exports = {execute};
