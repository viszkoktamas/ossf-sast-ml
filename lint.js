const fs = require("fs");
const acornLoose = require("acorn-loose");
const recast = require("recast");
const path = require('path');
const axios = require('axios');
const {globSync} = require('glob');

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
        functionsList.push({
            functionBody,
            startLine: root.loc.start.line,
            endLine: root.loc.end.line,
            nodeType: root.type
        });
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

function extractFunctionsFromPaths(paths, outFile) {
    if (!outFile) {
        outFile = 'result.json';
    }
    let data = [];
    paths.forEach((p) => {
        let ignoreFiles = [];
        let ignoreFileNames = ['.eslintignore', '.npmignore', '.gitignore'];
        ignoreFileNames.map((fileName) => {
            let ignoreFile = p + path.sep + fileName;
            if (fs.lstatSync(ignoreFile, {throwIfNoEntry: false})?.isFile()) {
                const fileContent = fs.readFileSync(ignoreFile, 'utf-8');
                ignoreFiles.push(...fileContent.split(/\r?\n/));
            }
        });
        const filesList = globSync('**/*.{js,ts,mjs,mts}', {
            ignore: ['**/node_modules/**', '**/java/**', '**/static/**', '**/spec/**',  '**/build/**', '**/docs/**', '**/*asset*/**', '**/min/**', '**/dist/**', '**/*demo*/**', '**/*sample*/**', '**/*test*/**', '**/*.min.js', '**/demo.*', '**/*test*.*', '**/*jquery*.*', ...ignoreFiles],
            cwd: p
        }).map((fp) => p + path.sep + fp);
        filesList.forEach((filePath) => {
            let messages = extractFunctionsFromFile(filePath);
            if (!messages.length) return;
            data.push({
                filePath: filePath,
                messages
            });
        });
    });
    fs.writeFileSync(outFile, JSON.stringify(data, null, 2), 'utf8');
    return outFile;
}

const execute = async (paths, output) => {
    console.log("Execute: (paths=", paths, ', output="' + output + '")');
    let outFile = extractFunctionsFromPaths(paths, output);
    try {
        const response = await axios({
            method: 'post',
            url: 'http://localhost:5000',
            headers: {'Content-Type': 'application/json'},
            data: {input_file: outFile}
        });
        console.log(response.data);
    } catch (e) {
        throw new Error("Could not run inference for " + outFile + ", error: " + e);
    }
    return outFile;
}


module.exports = {execute};
