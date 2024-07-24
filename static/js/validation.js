document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('signupForm');
    const inputs = form.querySelectorAll('input[data-validation]');

    inputs.forEach(input => {
        input.addEventListener('blur', validateField);
        input.addEventListener('input', validateField);
    });

    form.addEventListener('submit', validateForm);

    function validateField(event) {
        const input = event.target;
        const value = input.value.trim();
        const validationType = input.dataset.validation;
        let errorMessage = '';

        switch(validationType) {
            case 'name':
                if (value.length < 2) {
                    errorMessage = 'Name must be at least 2 characters long.';
                }
                break;
            case 'username':
                if (value.length < 3) {
                    errorMessage = 'Username must be at least 3 characters long.';
                } else {
                    checkUsernameAvailability(value);
                }
                break;
            case 'email':
                if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
                    errorMessage = 'Please enter a valid email address.';
                } else {
                    checkEmailAvailability(value);
                }
                break;
            case 'password':
                if (value.length < 8) {
                    errorMessage = 'Password must be at least 8 characters long.';
                }
                break;
        }

        setFieldValidity(input, errorMessage);
    }

    function setFieldValidity(input, errorMessage) {
        const errorElement = document.getElementById(`${input.id}Error`);
        if (errorMessage) {
            input.classList.add('is-invalid');
            errorElement.textContent = errorMessage;
        } else {
            input.classList.remove('is-invalid');
            errorElement.textContent = '';
        }
    }

    function validateForm(event) {
        let isValid = true;
        inputs.forEach(input => {
            validateField({target: input});
            if (input.classList.contains('is-invalid')) {
                isValid = false;
            }
        });
        if (!isValid) {
            event.preventDefault();
        }
    }

    function checkUsernameAvailability(username) {
        fetch(`/check-username/?username=${username}`)
            .then(response => response.json())
            .then(data => {
                if (!data.available) {
                    setFieldValidity(document.getElementById('username'), 'This username is already taken.');
                }
            });
    }

    function checkEmailAvailability(email) {
        fetch(`/check-email/?email=${email}`)
            .then(response => response.json())
            .then(data => {
                if (!data.available) {
                    setFieldValidity(document.getElementById('email'), 'This email is already registered.');
                }
            });
    }
});
