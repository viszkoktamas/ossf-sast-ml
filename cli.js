const optionator = require("optionator");
const lint = require("./lint");

module.exports = {
    async execute(args) {
        if (Array.isArray(args)) {
            console.log("CLI args: " + args.slice(2));
        }

        let opt;
        let options;

        try {
            opt = optionator({
                prepend: "my_module [options] [dir]",
                defaults: {
                    concatRepeatedArrays: true,
                    mergeRepeatedObjects: true
                },
                options: [
                    {
                        heading: "Output"
                    },
                    {
                        option: "output-file",
                        alias: "o",
                        type: "path::String",
                        default: "result.json",
                        description: "Specify file to write report to"
                    },
                    {
                        heading: "Miscellaneous"
                    },
                    {
                        option: "help",
                        alias: "h",
                        type: "Boolean",
                        description: "Show help"
                    }
                ]
            })
            options = opt.parse(args);
        } catch (error) {
            console.log(error.message);
            return 2;
        }

        if (options.help) {
            console.log(opt.generateHelp());
            return 0;
        }

        let files = options._;
        await lint.execute(files, options.outputFile);
        return 0;
    }
};
