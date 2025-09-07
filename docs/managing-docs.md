# Managing the Documentation

This documentation is built using [MkDocs](https://www.mkdocs.org/), a static site generator for project documentation.

## Adding a New Page

To add a new page to the documentation, follow these steps:

1.  Create a new markdown file (e.g., `new-page.md`) in the `docs/` directory.
2.  Add content to the new file using markdown syntax.
3.  Open the `mkdocs.yml` file in the root of the repository.
4.  Add a new entry to the `nav` section that points to your new file. For example:

    ```yaml
    nav:
      - Project Overview:
        - Home: index.md
        - ...
      - Services:
        - ...
        - New Page: new-page.md # Add your new page here
      - Business Case:
        - ...
    ```

5.  Save the `mkdocs.yml` file.

## `mkdocs.yml` Structure

The `mkdocs.yml` file is the main configuration file for the documentation site. Here's a brief overview of its structure:

*   `site_name`: The title of the documentation site.
*   `docs_dir`: The directory where the documentation source files are located.
*   `nav`: The navigation structure of the site. This is a list of pages and sections that will appear in the navigation bar.

For more information on configuring MkDocs, see the [official documentation](https://www.mkdocs.org/user-guide/configuration/).
