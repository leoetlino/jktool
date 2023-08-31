## Library and tool for MM3D GARs and layout files

Note: as of August 2023 this is not actively maintained. This readme was written 3 years ago and I never finished documenting the layout file formats and the library/tool. Sorry!

### Requirements
* Python 3.6+

### Usage

```
gar create  {files_to_include_in_archive}  {destination_archive}
gar update  {files_to_add_or_replace_in_archive}  {destination_archive}
gar extract {archive}
gar list {archive}
```

Pass -h to see a full list of commands or usage help for a specific command.
