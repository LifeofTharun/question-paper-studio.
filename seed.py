from app import app, db, Question

# CO assignment: Unit 1 → CO1, Unit 2 → CO2, etc.
sample_questions = [
    # Unit 1 — CO1 (K1, K6)
    Question(unit=1, k_level="K1", co="CO1", text="Define structured programming and list its key characteristics.", marks=2, difficulty="Easy", correct_answer="Structured programming is a technique using control structures (sequence, selection, iteration) with modular functions for better code organization and maintenance."),
    Question(unit=1, k_level="K1", co="CO1", text="State the primary steps involved in the software development life cycle.", marks=2, difficulty="Easy", correct_answer="Planning, Analysis, Design, Coding, Testing, Deployment, Maintenance"),
    Question(unit=1, k_level="K1", co="CO1", text="Differentiate a compiler and an interpreter with one example each.", marks=2, difficulty="Easy", correct_answer="Compiler: converts entire source code to machine code (C, C++). Interpreter: executes line-by-line (Python, JavaScript)."),
    Question(unit=1, k_level="K1", co="CO1", text="List the basic components of a C program with a simple example.", marks=2, difficulty="Easy", correct_answer="Header files, main function, variable declarations, executable statements, return statement."),
    Question(unit=1, k_level="K1", co="CO1", text="Define algorithm and flowchart. State their differences.", marks=2, difficulty="Easy", correct_answer="Algorithm: step-by-step procedure. Flowchart: graphical representation using symbols."),
    Question(unit=1, k_level="K1", co="CO1", text="State the rules for naming identifiers in C.", marks=2, difficulty="Easy", correct_answer="Start with letter/underscore, contain alphanumeric/underscore, case-sensitive, no spaces/reserved keywords."),
    Question(unit=1, k_level="K1", co="CO1", text="List the different data types available in C with their sizes.", marks=2, difficulty="Easy", correct_answer="int (4 bytes), float (4 bytes), double (8 bytes), char (1 byte), short (2 bytes), long (varies by system)."),
    Question(unit=1, k_level="K1", co="CO1", text="Define a token in C. List the types of tokens with examples.", marks=2, difficulty="Easy", correct_answer="Tokens are smallest units. Types: keywords, identifiers, constants, operators, delimiters, literals."),
    Question(unit=1, k_level="K1", co="CO1", text="State the purpose of header files in a C program.", marks=2, difficulty="Easy", correct_answer="Header files contain declarations of library functions and macros (e.g., stdio.h for I/O operations)."),
    Question(unit=1, k_level="K1", co="CO1", text="Define constants in C and list the types of constants.", marks=2, difficulty="Easy", correct_answer="Constants are fixed values. Types: integer, float, character, string constants."),
    Question(unit=1, k_level="K6", co="CO1", text="Design a complete C program demonstrating console input and output functions with proper formatting.", marks=10, difficulty="Awesome", correct_answer="Use printf with format specifiers (%d, %s, %f) and scanf for input. Include proper headers and main function."),
    Question(unit=1, k_level="K6", co="CO1", text="Formulate an error diagnostic report and outline debugging techniques for a faulty C program.", marks=5, difficulty="Awesome", correct_answer="Debugging: tracing, breakpoints, print statements, debuggers. Check logic and syntax errors."),
    Question(unit=1, k_level="K6", co="CO1", text="Develop a C program to demonstrate the use of all basic data types with scanf and printf.", marks=10, difficulty="Awesome", correct_answer="Program showing variable declarations of int, float, double, char with scanf input and printf output."),
    Question(unit=1, k_level="K6", co="CO1", text="Design a flowchart and C program to find the roots of a quadratic equation.", marks=10, difficulty="Awesome", correct_answer="Use formula: x = (-b ± √(b²-4ac)) / 2a. Include discriminant check for real/imaginary roots."),
    Question(unit=1, k_level="K6", co="CO1", text="Construct a C program to demonstrate type conversion and type casting with examples.", marks=5, difficulty="Awesome", correct_answer="Implicit (automatic) and explicit (forced) conversion. Example: (int)3.14 converts to 3."),
    Question(unit=1, k_level="K6", co="CO1", text="Develop a C program to swap two numbers using a temporary variable and without using one.", marks=5, difficulty="Medium", correct_answer="With temp: t=a; a=b; b=t. Without temp: a=a+b; b=a-b; a=a-b."),

    # Unit 2 — CO2 (K3)
    Question(unit=2, k_level="K3", co="CO2", text="Identify the purpose of variables, constants, and data types in a C program.", marks=2, difficulty="Easy", correct_answer="Variables store data values, constants hold fixed values, data types define value ranges and storage size."),
    Question(unit=2, k_level="K3", co="CO2", text="Solve the arithmetic expression: a = 10 + 5 * 2 % 4 - 3. Show step-by-step evaluation.", marks=2, difficulty="Medium", correct_answer="Following BODMAS: 5*2=10, 10%4=2, 10+2=12, 12-3=9. Result: a=9"),
    Question(unit=2, k_level="K3", co="CO2", text="Apply nested control structures to write a C program to find the largest of three numbers.", marks=5, difficulty="Medium", correct_answer="Use if-else with nested conditions or ternary operator to compare three values."),
    Question(unit=2, k_level="K3", co="CO2", text="Demonstrate the execution flow of a do-while loop compared to a standard while loop using a snippet.", marks=5, difficulty="Medium", correct_answer="do-while executes body first then checks condition. while checks first. do-while runs at least once."),
    Question(unit=2, k_level="K3", co="CO2", text="Construct a switch-case implementation in C to simulate a basic calculator.", marks=10, difficulty="Awesome", correct_answer="Use switch on operator (+,-,*,/), cases for each operation, default for invalid input."),
    Question(unit=2, k_level="K3", co="CO2", text="Write a C program using for loop to print the multiplication table of a given number.", marks=5, difficulty="Medium", correct_answer="for loop from 1 to 10, print num*i for each iteration."),
    Question(unit=2, k_level="K3", co="CO2", text="Construct a C program to check whether a number is prime or not using a while loop.", marks=10, difficulty="Awesome", correct_answer="Check divisibility from 2 to sqrt(n). If no divisor found, it's prime."),
    Question(unit=2, k_level="K3", co="CO2", text="Demonstrate the use of break and continue statements with suitable examples.", marks=5, difficulty="Medium", correct_answer="break exits loop early. continue skips current iteration. Example: skip even numbers or exit on condition."),

    # Unit 3 — CO3 (K3, K4)
    Question(unit=3, k_level="K3", co="CO3", text="List two practical uses of arrays in programming and state their indexing rule.", marks=2, difficulty="Easy", correct_answer="Uses: storing multiple values, tabular data. Indexing: 0-based (first element at index 0)."),
    Question(unit=3, k_level="K3", co="CO3", text="Demonstrate the memory layout and initialization of a two-dimensional array in C.", marks=2, difficulty="Easy", correct_answer="2D array as array of arrays. Initialization: arr[rows][cols] = {{...}}. Stored in row-major order."),
    Question(unit=3, k_level="K3", co="CO3", text="Apply linear search logic to find an element inside an integer array.", marks=5, difficulty="Medium", correct_answer="Loop through array comparing each element with target. Return index if found, -1 if not found."),
    Question(unit=3, k_level="K4", co="CO3", text="Analyze the time complexity and working mechanism of the Bubble sort algorithm with an example.", marks=10, difficulty="Awesome", correct_answer="Compares adjacent elements, swaps if wrong order. Time: O(n²). Best: O(n) for sorted array."),
    Question(unit=3, k_level="K4", co="CO3", text="Examine string handling functions in C and compare standard input/output methods.", marks=5, difficulty="Awesome", correct_answer="strcpy, strlen, strcat, strcmp. I/O: gets/puts (string), scanf/printf (formatted)."),
    Question(unit=3, k_level="K3", co="CO3", text="Write a C program to find the largest element in a one-dimensional array.", marks=5, difficulty="Medium", correct_answer="Iterate through array, maintain max variable, update if element > max."),
    Question(unit=3, k_level="K4", co="CO3", text="Analyze the selection sort algorithm and implement it in C with a trace for 5 elements.", marks=10, difficulty="Awesome", correct_answer="Find minimum, swap with current position. Repeat. Time: O(n²). Example: 64,25,12,22,11 → 11,12,22,25,64"),
    Question(unit=3, k_level="K3", co="CO3", text="Demonstrate matrix addition using two-dimensional arrays in C.", marks=5, difficulty="Medium", correct_answer="Add corresponding elements: C[i][j] = A[i][j] + B[i][j]. Requires same dimensions."),

    # Unit 4 — CO4 (K6)
    Question(unit=4, k_level="K6", co="CO4", text="Explain the role of a return statement and parameters in a user-defined function.", marks=2, difficulty="Easy", correct_answer="Parameters pass data to function. Return statement sends result back to caller, stops execution."),
    Question(unit=4, k_level="K6", co="CO4", text="Define function prototypes and explain their necessity in modular programming.", marks=2, difficulty="Easy", correct_answer="Prototype declares function signature before definition. Enables compilation and modular design."),
    Question(unit=4, k_level="K6", co="CO4", text="Formulate a recursive function in C to calculate the factorial of a given integer.", marks=5, difficulty="Medium", correct_answer="Base case: n==0 return 1. Recursive: return n*factorial(n-1)."),
    Question(unit=4, k_level="K6", co="CO4", text="Develop a complete C program that passes multi-dimensional arrays to user-defined functions.", marks=10, difficulty="Awesome", correct_answer="Pass 2D array as parameter with fixed column size. Process each element in nested loops."),
    Question(unit=4, k_level="K6", co="CO4", text="Construct a modular program structure demonstrating call-by-value and call-by-reference mechanics.", marks=5, difficulty="Awesome", correct_answer="Call-by-value: copy passed. Changes don't affect original. Call-by-reference: pointer passed, changes affect original."),
    Question(unit=4, k_level="K6", co="CO4", text="Design a C program using recursion to compute the nth Fibonacci number.", marks=10, difficulty="Awesome", correct_answer="Base: F(0)=0, F(1)=1. Recursive: F(n)=F(n-1)+F(n-2). Example: F(5)=5"),
    Question(unit=4, k_level="K6", co="CO4", text="Develop a C program to demonstrate the use of storage classes: auto, static, extern, register.", marks=5, difficulty="Awesome", correct_answer="auto: default, local scope. static: retains value. extern: external variable. register: CPU register."),
    Question(unit=4, k_level="K6", co="CO4", text="Construct a C program to find the GCD of two numbers using a recursive function.", marks=5, difficulty="Medium", correct_answer="Base: if b==0 return a. Recursive: return gcd(b, a%b). Example: GCD(48,18)=6"),

    # Unit 5 — CO5 (K6)
    Question(unit=5, k_level="K6", co="CO5", text="State two differences between a pointer and an ordinary integer variable.", marks=2, difficulty="Easy", correct_answer="Pointer stores address, integer stores value. Pointer uses * and & operators."),
    Question(unit=5, k_level="K6", co="CO5", text="Define pointer declarations and explain how memory addresses are accessed in C.", marks=2, difficulty="Easy", correct_answer="Syntax: type *ptr;. & gets address, * dereferences to get value."),
    Question(unit=5, k_level="K6", co="CO5", text="Construct a C program using dynamic memory allocation functions (malloc, free).", marks=5, difficulty="Medium", correct_answer="malloc allocates, free deallocates. Example: int *p = (int*)malloc(sizeof(int)); free(p);"),
    Question(unit=5, k_level="K6", co="CO5", text="Explain the difference between stack and heap memory with a suitable C example.", marks=5, difficulty="Awesome", correct_answer="Stack: automatic, local variables, limited size. Heap: dynamic, malloc/free, larger size."),
    Question(unit=5, k_level="K6", co="CO5", text="Develop a program utilizing self-referential structures and file handling operations to store records.", marks=10, difficulty="Awesome", correct_answer="Struct with pointer to self (linked list). fopen, fwrite/fread for file operations, fclose."),
    Question(unit=5, k_level="K6", co="CO5", text="Design a file management system snippet in C to read and write structured student data.", marks=5, difficulty="Awesome", correct_answer="fopen in 'w' mode for write, 'r' for read. fwrite/fread for struct data. Proper error handling."),
    Question(unit=5, k_level="K6", co="CO5", text="Develop a C program to demonstrate pointer arithmetic with arrays.", marks=5, difficulty="Medium", correct_answer="ptr++, ptr--, ptr[i] equivalent to *(ptr+i). Works for dynamic arrays."),
    Question(unit=5, k_level="K6", co="CO5", text="Construct a C program using structures to store and display student records.", marks=10, difficulty="Awesome", correct_answer="struct definition with fields (name, roll, marks). Input/output functions for 'n' students."),
]

with app.app_context():
    db.create_all()
    Question.query.delete()
    db.session.bulk_save_objects(sample_questions)
    db.session.commit()
    print("Database seeded successfully!")