# Website Product Bulk Publish

![Odoo Version](https://img.shields.io/badge/Odoo-17.0-blue)
![License](https://img.shields.io/badge/license-LGPL--3-green)

## Overview

This module extends Odoo's product management functionality by adding bulk publish and unpublish actions for products on the website. Instead of editing products one by one, you can now manage website visibility for multiple products simultaneously.

## Features

- **Bulk Publish**: Publish multiple products on the website with a single action
- **Bulk Unpublish**: Unpublish multiple products from the website at once
- **Smart Filtering**: Automatically filters already published/unpublished products
- **User Notifications**: Shows informative notifications with the number of products affected
- **Performance Optimized**: Uses bulk write operations for better performance
- **Audit Trail**: Logs all operations for tracking and debugging

## Installation

1. Download or clone this module into your Odoo addons directory
2. Update the apps list: Go to Apps > Update Apps List
3. Search for "Website Product Bulk Publish"
4. Click Install

## Configuration

No additional configuration is required. The module works out of the box.

## Usage

### Publishing Products

1. Navigate to **Products > Products**
2. Select multiple products from the list view (use checkboxes)
3. Click the **Action** dropdown menu
4. Select **Publish on Website**
5. A notification will appear showing how many products were published

### Unpublishing Products

1. Navigate to **Products > Products**
2. Select multiple products from the list view (use checkboxes)
3. Click the **Action** dropdown menu
4. Select **Unpublish from Website**
5. A notification will appear showing how many products were unpublished

## Technical Details

### Dependencies

- `website`: Required for website publishing functionality
- `product`: Base product management module

### Models Extended

- `product.template`: Adds bulk publish/unpublish methods

### Server Actions

- `action_publish_products_website`: Publishes selected products
- `action_unpublish_products_website`: Unpublishes selected products

### Methods

#### `action_publish_on_website()`

Publishes selected products on the website by setting `is_published=True`.

- Filters products that are not already published
- Uses bulk write operations for performance
- Returns a notification action with results
- Logs the operation

#### `action_unpublish_from_website()`

Unpublishes selected products from the website by setting `is_published=False`.

- Filters products that are currently published
- Uses bulk write operations for performance
- Returns a notification action with results
- Logs the operation

## Best Practices Implemented

This module follows Odoo 17 best practices:

- ✅ Proper docstrings for all methods
- ✅ Logging for audit trail
- ✅ User notifications for feedback
- ✅ Bulk operations for performance
- ✅ Smart filtering to avoid unnecessary writes
- ✅ Proper exception handling
- ✅ Use of translatable strings with `_()`
- ✅ Copyright headers and license information
- ✅ Minimal and clean code structure
- ✅ No unnecessary access rights files

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Follow Odoo coding guidelines
2. Add tests for new features
3. Update documentation as needed
4. Test thoroughly before submitting

## Support

For issues, questions, or contributions, please contact:

**Author**: Diego Venegas

## License

This module is licensed under LGPL-3.0.

---

Copyright 2024 Diego Venegas
