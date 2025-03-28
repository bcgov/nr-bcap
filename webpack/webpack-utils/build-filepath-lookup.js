/* eslint-disable */

const Path = require('path');
const fs = require('fs');

function buildFilepathLookup(path, staticUrlPrefix) {
    path = path.replace(/\\/g, '/')
    if (!fs.existsSync(path)) {
        return;
    }

    const prefix = path.match(/[^/]+$/);
    const staticUrl = staticUrlPrefix ? staticUrlPrefix : "";

    const getFileList = function (dirPath) {
        return fs.readdirSync(dirPath, { withFileTypes: true }).reduce((fileList,entries) => {
            const childPath = Path.join(dirPath, entries.name).replace(/\\/g, '/');

            if (entries.isDirectory()) {
                fileList.push(...getFileList(childPath, fileList));
            } else
            {
                fileList.push(childPath);
            }
            return fileList;
            }, []);
        };

    return getFileList(path).reduce((lookup, file) => {
        // Ignore dotfiles
        if (file.match(new RegExp(Path.sep + '\\.')) || file.match(/^\./)) {
            return lookup;
        }
        const extension = file.match(/[^.]+$/).toString();
        const extensionReplacementRegex = new RegExp(`\\.${extension}$`);

        if (extension === 'js') {
            lookup[file.replace(path,'').replace(/\\/g, '/').replace(extensionReplacementRegex,'').replace(/^\//,'')] = {"import": file, "filename": `${prefix}/[name].${extension}`};
        }
        else if (extension === 'css' || extension === 'scss') {
            lookup[Path.join('css', file.replace(path,'')).replace(/\\/g, '/').replace(extensionReplacementRegex,'').replace(/^\//,'')] = { 'import': file };
        }
        else {
            // staticUrl used for images
            lookup[`${staticUrl}${prefix}/${file.replace(path,'').replace(/\\/g, '/').replace(/^\//,'')}`] = file;
        }
        return lookup;
    }, {});
}

function toDockerOrGitHubPath(path) {
    if (process.env.GITHUB_ACTIONS && typeof path === 'string' && path.startsWith('/web_root/')) {
        const workspace = process.cwd();
        return path.replace('/web_root/', `${workspace}/`);
    }

    return path;
}

module.exports = { buildFilepathLookup, toDockerOrGitHubPath };
