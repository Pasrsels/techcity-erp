class CustomSearchSelect {
      constructor(containerId, options = {}) {
            this.container = document.getElementById(containerId);
            this.input = this.container.querySelector('.search-input');
            this.dropdown = this.container.querySelector('.dropdown');
            this.hiddenInput = options.hiddenInput;
            this.data = options.data || [];
            this.newOptions = []; 
            this.placeholder = options.placeholder || 'Search...';
            this.onSelect = options.onSelect || (() => {});
            this.onAddNew = options.onAddNew || (() => {});
            this.selectedValue = null;
            this.selectedText = null;
            this.highlightedIndex = -1;
            this.filteredData = [...this.data];
            this.allowAddNew = options.allowAddNew !== false; 

            this.init();
        }

        init() {
            this.input.placeholder = this.placeholder;
            this.bindEvents();
        }

        bindEvents() {
            this.input.addEventListener('input', (e) => this.handleInput(e));
            this.input.addEventListener('focus', () => this.showDropdown());
            this.input.addEventListener('keydown', (e) => this.handleKeydown(e));

            document.addEventListener('click', (e) => {
                if (!this.container.contains(e.target)) {
                    this.hideDropdown();
                }
            });
        }

        handleInput(e) {
            const query = e.target.value.toLowerCase().trim();
            
            this.filteredData = this.data.filter(item => 
                item.name.toLowerCase().includes(query)
            );

            this.highlightedIndex = -1;
            this.renderDropdown(query);
            this.showDropdown();
        }

        handleKeydown(e) {
            const totalItems = this.getTotalDropdownItems();
            
            switch(e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    this.highlightedIndex = Math.min(this.highlightedIndex + 1, totalItems - 1);
                    this.updateHighlight();
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    this.highlightedIndex = Math.max(this.highlightedIndex - 1, -1);
                    this.updateHighlight();
                    break;
                case 'Enter':
                    e.preventDefault();
                    this.handleEnterKey();
                    break;
                case 'Escape':
                    this.hideDropdown();
                    this.input.blur();
                    break;
            }
        }

        handleEnterKey() {
            if (this.highlightedIndex >= 0) {
                const isAddNewOption = this.highlightedIndex >= this.filteredData.length;
                
                if (isAddNewOption) {
                    const newText = this.input.value.trim();
                    this.addNewOption(newText);
                } else {
                    this.selectItem(this.filteredData[this.highlightedIndex]);
                }
            }
        }

        getTotalDropdownItems() {
            let total = this.filteredData.length;
            
            const query = this.input.value.trim();
            if (this.shouldShowAddNew(query)) {
                total += 1;
            }
            
            return total;
        }

        shouldShowAddNew(query) {
            if (!this.allowAddNew || !query) return false;

            const exactMatch = this.data.some(item => 
                item.name.toLowerCase() === query.toLowerCase()
            );
            
            return !exactMatch;
        }

        showDropdown() {
            const query = this.input.value.trim();
            if (this.filteredData.length > 0 || this.shouldShowAddNew(query)) {
                this.renderDropdown(query);
                this.dropdown.classList.add('show');
            }
        }

        hideDropdown() {
            this.dropdown.classList.remove('show');
            this.highlightedIndex = -1;
        }

        renderDropdown(query = '') {
            let html = '';
            
            // Render existing filtered options
            if (this.filteredData.length === 0 && !this.shouldShowAddNew(query)) {
                html = '<div class="no-results">No results found</div>';
            } else {
                html = this.filteredData.map((item, index) => `
                    <div class="dropdown-item" data-index="${index}" data-type="existing">
                        ${item.name}
                        ${this.newOptions.includes(item.value) ? '<span class="new-option-badge">NEW</span>' : ''}
                    </div>
                `).join('');
                
                // Add "Add new" option if applicable
                if (this.shouldShowAddNew(query)) {
                    html += `
                        <div class="dropdown-item add-new" data-type="add-new">
                            <span class="add-icon">+</span>
                            Add "${query}"
                        </div>
                    `;
                }
            }

            this.dropdown.innerHTML = html;

            // Add click listeners
            this.dropdown.querySelectorAll('.dropdown-item').forEach((item, index) => {
                item.addEventListener('click', () => {
                    const type = item.dataset.type;
                    
                    if (type === 'add-new') {
                        this.addNewOption(query);
                    } else {
                        const dataIndex = parseInt(item.dataset.index);
                        this.selectItem(this.filteredData[dataIndex]);
                    }
                });
            });
        }

        updateHighlight() {
            const items = this.dropdown.querySelectorAll('.dropdown-item');
            items.forEach((item, index) => {
                item.classList.toggle('highlighted', index === this.highlightedIndex);
            });

            if (this.highlightedIndex >= 0 && items[this.highlightedIndex]) {
                items[this.highlightedIndex].scrollIntoView({
                    block: 'nearest',
                    behavior: 'smooth'
                });
            }
        }

        addNewOption(text) {
            if (!text) return;
            
            // Create new option with unique value
            const newOption = {
                value: `new_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                text: text,
                isNew: true
            };
            
            // Add to data arrays
            this.data.push(newOption);
            this.newOptions.push(newOption.value);
            
            // Select the new option
            this.selectItem(newOption);
            
            // Callback for handling new options
            this.onAddNew(newOption);
        }

        selectItem(item) {
            this.selectedValue = item.value;
            this.selectedText = item.text;
            this.input.value = item.text;
            
            // Update hidden input if provided
            if (this.hiddenInput) {
                this.hiddenInput.value = item.value;
            }
            
            this.hideDropdown();
            this.onSelect(item);
        }

        setValue(value, text) {
            this.selectedValue = value;
            this.selectedText = text;
            this.input.value = text;
            
            if (this.hiddenInput) {
                this.hiddenInput.value = value;
            }
        }

        getValue() {
            return {
                value: this.selectedValue,
                text: this.selectedText,
                isNew: this.newOptions.includes(this.selectedValue)
            };
        }

        getNewOptions() {
            return this.data.filter(item => this.newOptions.includes(item.value));
        }

        setData(newData) {
            this.data = newData.map(item => {
                if (typeof item === 'string') {
                    return { value: item, text: item };
                }
                return item;
            });
            this.filteredData = [...this.data];
        }
    }